// コメントの入力。詳細パネルと詳細の全画面の下端と、コメントの一覧の下端に留める、コメントをレビュー中に溜める入力欄と「レビューに追加」のボタン。選んだ箇所を添えられ、溜めた結果を入力の近くに出す。

namespace MindmapPreview {
  /** 溜める状態。idle は結果を出さない */
  export type SendStatus = "idle" | "saving" | "saved" | "empty" | "failed" | "sent" | "inserted" | "voice-failed";

  /** 音声入力の状態 */
  export type VoicePhase = "idle" | "disabled" | "recording" | "transcribing";

  /** ✓ を押したときの入力欄の中身とカーソルの位置 */
  export type VoiceDoneInput = { body: string; start: number; end: number };

  /** 音声入力のボタンの引数（コメントの入力と返信の入力で共通） */
  export type VoiceProps = {
    /** 音声入力の状態 */
    voice?: VoicePhase;
    /** マイクのボタンを押せない理由（`voice` が `disabled` のとき） */
    voiceReason?: string | null;
    /** 録音を始めてからの秒数（`voice` が `recording` のとき） */
    elapsed?: number;
    /** `status` が `sent` のとき、Claude Code へ入力したか */
    entered?: boolean;
  };

  /** 音声入力のボタンのコールバック */
  export type VoiceHandlers = {
    /** マイクのボタン（`idle`） */
    voiceStart?: () => void;
    /** 録音中の × */
    voiceCancel?: () => void;
    /** 録音中の ✓（入力欄の中身とカーソルの位置） */
    voiceDone?: (input: VoiceDoneInput) => void;
    /** 押せないマイクのボタン */
    voiceBlocked?: () => void;
  };

  /** コメントの入力の引数 */
  export type SendFormProps = VoiceProps & {
    /** コメントを向ける項目の ID。ラベル「{ID} へのコメント」に等幅で出す。null は項目を指さないコメント（ラベルを見せず `aria-label` に持つ） */
    target: string | null;
    /** 添えた箇所。入力欄の上に箇所の名前と選んだ文（3 行まで）と × を出す */
    loc?: Location | null;
    /** 入力欄の中身 */
    body?: string;
    status?: SendStatus;
    /** 溜めた後のレビュー中のコメントの件数。`saved` のとき出す */
    count?: number | null;
    /** サーバーが返した溜められなかった理由。`failed` で null なら、サーバーに届かなかったとして立ち上げ直しの案内と本文のコピーのボタンを出す */
    detail?: string | null;
    /** 畳んだ形（`target` が null のときだけ使う） */
    collapsed?: boolean;
    /** `target` が null のときの入力欄の読み上げの名前（コメントの一覧の新しいスレッドの入力は「新しいスレッド」） */
    label?: string;
    /** 開いているか（`target` があるときだけ使う）。偽なら見出しの行だけを出す */
    open?: boolean;
    on: VoiceHandlers & {
      /** 入力欄の中身が変わったとき */
      input: (body: string) => void;
      /** 「レビューに追加」か Ctrl+Enter（macOS は Cmd+Enter）。`saving` の間は呼ばない */
      save: (body: string) => void;
      /** 添えた箇所の × を押したとき */
      unquote: () => void;
      /** 本文のコピーのボタンを押したとき */
      copy: (body: string) => void;
      /** 入力欄に入ったとき */
      focus: () => void;
      /** 部品の外へ出たとき */
      blur: () => void;
      /** 開閉のボタンを押したとき（押した後の開閉） */
      toggle?: (open: boolean) => void;
    };
  };

  /** 溜めている印と文言を出すまでの待ち（ミリ秒）。すぐ終わる処理では点滅させない */
  const SENDING_NOTICE_DELAY_MS = 1000;

  /** 項目を指さないコメントの入力欄の読み上げの名前 */
  const NO_TARGET_LABEL = "項目を指さないコメント";

  /** 入力欄の ID に付ける連番（同じ文書に複数置いても ID が重ならないように） */
  let sendFormSequence = 0;

  /** UTC のタイムゾーン付き ISO 8601 を JST の `MM/DD HH:mm` にする */
  export function formatJst(iso: string): string {
    const parts = new Intl.DateTimeFormat("ja-JP", {
      timeZone: "Asia/Tokyo",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(new Date(iso));
    const part = (type: Intl.DateTimeFormatPartTypes): string =>
      parts.find((entry) => entry.type === type)?.value ?? "";
    return `${part("month")}/${part("day")} ${part("hour")}:${part("minute")}`;
  }

  /** 結果の要素の中身（状態ごとの印と文言） */
  function resultContent({
    status,
    count,
    detail,
    onCopy,
  }: Pick<SendFormProps, "status" | "count" | "detail"> & { onCopy: () => void }): Child[] {
    if (status === "saved") {
      return [icon("check"), h({ tag: "span", children: [`レビューに追加しました（レビュー中 ${count ?? 0} 件）。`] })];
    }
    if (status === "empty") {
      return [icon("alert"), h({ tag: "span", children: ["コメントを入れてから追加してください。"] })];
    }
    if (status === "failed") {
      // サーバーが理由を返した: 理由を出す
      if (detail !== null && detail !== undefined) {
        return [icon("alert"), h({ tag: "span", children: [`レビューに追加できませんでした。${detail}`] })];
      }
      // サーバーに届かなかった: 立ち上げ直すと URL が変わり、書きかけは引き継がれないので、本文をコピーする手段を添える
      return [
        icon("alert"),
        h({
          tag: "span",
          attrs: { class: "send-msg-body" },
          children: [
            h({
              tag: "span",
              children: [
                "レビューに追加できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから追加してください。",
              ],
            }),
            h({
              tag: "button",
              attrs: { class: "icon-btn send-copy", type: "button", "aria-label": "本文をコピー", title: "本文をコピー", onclick: onCopy },
              children: [icon("copy")],
            }),
          ],
        }),
      ];
    }
    return [];
  }

  /** 音声入力の結果（送信した・挿入した・失敗した）の中身。音声入力の結果でなければ null */
  export function voiceResultContent(status: string | undefined, detail: string | null | undefined, entered = false): Child[] | null {
    if (status === "sent") {
      return [icon("check"), h({ tag: "span", children: [entered ? "送信し、Claude Code へ入力しました。" : "送信しました。Claude Code へは入力していません。"] })];
    }
    if (status === "inserted") {
      return [icon("check"), h({ tag: "span", children: ["文字起こしの結果を挿入しました。"] })];
    }
    if (status === "voice-failed") {
      return [icon("alert"), h({ tag: "span", children: [detail ?? VOICE_TEXT.failed] })];
    }
    return null;
  }

  /** 録音中・文字起こし中の結果の行の中身。どちらでもなければ null */
  export function voiceProgressContent(voice: VoicePhase, elapsed: number): Child[] | null {
    if (voice === "recording") {
      // 録音中: 丸と経過の時間は見た目だけにし、読み上げは「録音中」だけにする
      return [
        h({ tag: "span", attrs: { class: "rec-dot", "aria-hidden": "true" } }),
        h({ tag: "span", attrs: { class: "sr-only" }, children: ["録音中"] }),
        h({ tag: "span", attrs: { class: "rec-time", "aria-hidden": "true" }, children: [formatElapsed(elapsed)] }),
      ];
    }
    if (voice === "transcribing") {
      return [
        h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }),
        h({ tag: "span", attrs: { class: "sr-only" }, children: ["文字起こししています。"] }),
      ];
    }
    return null;
  }

  /** 結果の行のクラスの状態（録音中・文字起こし中は音声の状態を優先する） */
  export function messageState(voice: VoicePhase, status: string): string {
    if (voice === "recording") return "recording";
    if (voice === "transcribing") return "saving";
    return status;
  }

  /** 音声入力のボタンを入れる連番（ツールチップの ID が重ならないように） */
  let voiceSequence = 0;

  /**
   * 入力欄の右に並べる音声入力のボタン。
   * idle・disabled はマイクのボタンと submit を、recording・transcribing は × と ✓ を返す。
   */
  export function voiceButtons({
    voice,
    voiceReason,
    textarea,
    submit,
    on,
  }: {
    voice: VoicePhase;
    voiceReason: string | null;
    textarea: HTMLTextAreaElement;
    submit: HTMLElement;
    on: VoiceHandlers;
  }): Child[] {
    if (voice === "recording" || voice === "transcribing") {
      const busy = voice === "transcribing";
      return [
        h({
          tag: "div",
          attrs: { class: "send-rec-actions" },
          children: [
            h({
              tag: "button",
              attrs: {
                class: "icon-btn send-rec-cancel",
                type: "button",
                "aria-label": "キャンセル",
                title: "キャンセル（録音を破棄）",
                disabled: busy,
                onclick: () => on.voiceCancel?.(),
              },
              children: [icon("x")],
            }),
            h({
              tag: "button",
              attrs: {
                class: "icon-btn send-rec-done",
                type: "button",
                "aria-label": busy ? "文字起こし中" : "文字起こし",
                title: busy ? "文字起こし中" : "文字起こし",
                disabled: busy,
                "data-saving": busy ? "" : null,
                onclick: () =>
                  on.voiceDone?.({ body: textarea.value, start: textarea.selectionStart, end: textarea.selectionEnd }),
              },
              children: [busy ? h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }) : icon("check")],
            }),
          ],
        }),
      ];
    }
    const blocked = voice === "disabled";
    voiceSequence += 1;
    const tipId = `voice-tip-${voiceSequence}`;
    const mic = h({
      tag: "button",
      attrs: {
        class: "icon-btn send-mic",
        type: "button",
        "aria-label": "音声で入力",
        title: blocked ? (voiceReason ?? "") : "音声で入力",
        // 押せないときもフォーカスを受けたまま、理由をツールチップで指す
        "aria-disabled": blocked ? "true" : null,
        "aria-describedby": blocked ? tipId : null,
        onclick: () => (blocked ? on.voiceBlocked?.() : on.voiceStart?.()),
      },
      children: [icon("mic")],
    });
    const micPart = blocked
      ? h({
          tag: "span",
          attrs: { class: "send-tip-wrap" },
          children: [mic, h({ tag: "span", attrs: { class: "send-tip", role: "tooltip", id: tipId }, children: [voiceReason ?? ""] })],
        })
      : mic;
    return [micPart, submit];
  }

  /** 添えた箇所（名前・選んだ文・外す ×）の要素 */
  function locationChip({ loc, id, onUnquote }: { loc: Location; id: string; onUnquote: () => void }): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "send-loc", id },
      children: [
        h({
          tag: "div",
          attrs: { class: "send-loc-head" },
          children: [
            h({ tag: "span", attrs: { class: "send-loc-name" }, children: [locationLabel(loc)] }),
            h({
              tag: "button",
              attrs: { class: "icon-btn send-unquote", type: "button", "aria-label": "箇所を外す", title: "箇所を外す", onclick: onUnquote },
              children: [icon("x")],
            }),
          ],
        }),
        h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [loc.text] }),
      ],
    });
  }

  /** 項目へのコメントをレビュー中に溜める入力欄と「レビューに追加」のボタン、結果を返す */
  export function sendForm({
    target,
    loc = null,
    body = "",
    status = "idle",
    count = null,
    detail = null,
    collapsed = false,
    label = NO_TARGET_LABEL,
    open = true,
    voice = "idle",
    voiceReason = null,
    elapsed = 0,
    entered = false,
    on,
  }: SendFormProps): HTMLFormElement {
    sendFormSequence += 1;
    const fieldId = `send-${sendFormSequence}`;
    const messageId = `${fieldId}-msg`;
    const locId = `${fieldId}-loc`;
    const bodyId = `${fieldId}-body`;
    /** 畳むのは、項目を指さない入力だけ */
    const folded = collapsed && target === null;

    /** 溜めている間は溜めない。それ以外は入力欄の中身そのままを渡す */
    const trySave = (): void => {
      if (status === "saving") return;
      on.save(textarea.value);
    };

    const textarea = h({
      tag: "textarea",
      attrs: {
        id: fieldId,
        name: "body",
        rows: 1,
        "aria-label": target === null ? label : null,
        "aria-describedby": folded ? null : target !== null && loc !== null ? `${locId} ${messageId}` : messageId,
        "aria-keyshortcuts": "Control+Enter",
        // 溜めている間と文字起こし中は書き換えられない
        readonly: status === "saving" || voice === "transcribing",
        // 本文が空で溜めようとした: 入力の誤りとして示す
        "aria-invalid": status === "empty" ? "true" : null,
        oninput: () => on.input(textarea.value),
        onfocus: () => on.focus(),
        onkeydown: (event) => {
          const key = event as KeyboardEvent;
          // 変換の確定の Enter では溜めない
          if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
            key.preventDefault();
            trySave();
          }
        },
      },
      children: [body],
    });

    const shownState = messageState(voice, status);
    const message = h({
      tag: "p",
      attrs: { class: shownState === "idle" ? "send-msg" : `send-msg ${shownState}`, id: messageId, role: "status" },
      children:
        voiceProgressContent(voice, elapsed) ??
        voiceResultContent(status, detail, entered) ??
        resultContent({ status, count, detail, onCopy: () => on.copy(textarea.value) }),
    });
    // 溜めている印と文言は、待ちの後に入れる
    if (status === "saving") {
      window.setTimeout(() => {
        message.replaceChildren(
          h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }),
          h({ tag: "span", children: ["レビューに追加しています"] }),
        );
      }, SENDING_NOTICE_DELAY_MS);
    }

    const form = h({
      tag: "form",
      attrs: {
        class: `send send-footer${folded ? " collapsed" : ""}`,
        novalidate: true,
        "data-id": target,
        onsubmit: (event) => {
          event.preventDefault();
          trySave();
        },
        onfocusout: (event) => {
          // フォーカスが部品の外へ出たときだけ知らせる
          const next = (event as FocusEvent).relatedTarget as Node | null;
          if (next === null || !form.contains(next)) on.blur();
        },
      },
      children: target === null ? [textareaLine(), folded ? null : message] : [head(), formBody()],
    });
    return form;

    /** 入力欄と、その右の「レビューに追加」（アイコンだけのボタン）の行 */
    function textareaLine(): HTMLElement | HTMLTextAreaElement {
      if (folded) return textarea;
      const submit = h({
        tag: "button",
        attrs: {
          class: "icon-btn send-submit",
          type: "submit",
          "aria-label": "レビューに追加",
          title: "レビューに追加（Ctrl+Enter）",
          disabled: status === "saving",
          // 溜めている間は処理中のカーソルにする
          "data-saving": status === "saving" ? "" : null,
        },
        children: [icon("comment")],
      });
      return h({
        tag: "div",
        attrs: { class: "send-line" },
        children: [textarea, ...voiceButtons({ voice, voiceReason, textarea, submit, on })],
      });
    }

    /** 見出しの行（「{ID} へのコメント」・書きかけの印・開閉のボタン） */
    function head(): HTMLElement {
      const toggleLabel = open ? "コメントの入力を閉じる" : "コメントの入力を開く";
      return h({
        tag: "div",
        attrs: { class: "send-head" },
        children: [
          h({
            tag: open ? "label" : "span",
            attrs: { class: "send-label", for: open ? fieldId : null },
            children: [h({ tag: "span", attrs: { class: "mono" }, children: [target ?? ""] }), " へのコメント"],
          }),
          !open && body.trim() !== ""
            ? h({ tag: "span", attrs: { class: "send-draft" }, children: [icon("edit"), "書きかけ"] })
            : null,
          h({
            tag: "button",
            attrs: {
              class: "icon-btn send-toggle",
              type: "button",
              "aria-expanded": open ? "true" : "false",
              "aria-controls": bodyId,
              "aria-label": toggleLabel,
              title: toggleLabel,
              onclick: () => on.toggle?.(!open),
            },
            children: [icon("chev")],
          }),
        ],
      });
    }

    /** 開閉する範囲（添えた箇所・入力欄の行・結果） */
    function formBody(): HTMLElement {
      return h({
        tag: "div",
        attrs: { class: "send-body", id: bodyId, hidden: !open },
        children: [loc !== null ? locationChip({ loc, id: locId, onUnquote: on.unquote }) : null, textareaLine(), message],
      });
    }
  }
}
