// コメントの入力。詳細パネルと詳細の全画面の下端と、コメントの一覧の下端に留める、コメントをレビュー中に溜める入力欄と「レビューに追加」のボタン。選んだ箇所を添えられ、溜めた結果を入力の近くに出す。

namespace MindmapPreview {
  /** 溜める状態。idle は結果を出さない */
  export type SendStatus = "idle" | "saving" | "saved" | "empty" | "failed";

  /** コメントの入力の引数 */
  export type SendFormProps = {
    /** コメントを向ける項目の ID。ラベル「{ID} へのコメント」に等幅で出す。null は項目を指さないコメント（ラベルを見せず `aria-label` に持つ） */
    target: string | null;
    /** 添えた箇所。入力欄の上に箇所の名前と選んだ文（3 行まで）と × を出す */
    loc?: Location | null;
    /** 入力欄の中身 */
    body?: string;
    status?: SendStatus;
    /** 溜めた後のレビュー中のコメントの件数。`saved` のとき出す */
    count?: number | null;
    /** サーバーが返した溜められなかった理由。`failed` で null なら、サーバーに届かなかったとして立ち上げ直しの案内と「本文を写す」を出す */
    detail?: string | null;
    /** 畳んだ形（`target` が null のときだけ使う） */
    collapsed?: boolean;
    on: {
      /** 入力欄の中身が変わったとき */
      input: (body: string) => void;
      /** 「レビューに追加」か Ctrl+Enter（macOS は Cmd+Enter）。`saving` の間は呼ばない */
      save: (body: string) => void;
      /** 添えた箇所の × を押したとき */
      unquote: () => void;
      /** 「本文を写す」を押したとき */
      copy: (body: string) => void;
      /** 入力欄に入ったとき */
      focus: () => void;
      /** 部品の外へ出たとき */
      blur: () => void;
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
      // サーバーに届かなかった: 立ち上げ直すと URL が変わり、書きかけは引き継がれないので、本文を写す手段を添える
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
              attrs: { class: "btn ghost send-copy", type: "button", onclick: onCopy },
              children: [icon("copy"), "本文を写す"],
            }),
          ],
        }),
      ];
    }
    return [];
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
    on,
  }: SendFormProps): HTMLFormElement {
    sendFormSequence += 1;
    const fieldId = `send-${sendFormSequence}`;
    const messageId = `${fieldId}-msg`;
    const locId = `${fieldId}-loc`;
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
        rows: folded ? 1 : 2,
        "aria-label": target === null ? NO_TARGET_LABEL : null,
        "aria-describedby": folded ? null : target !== null && loc !== null ? `${locId} ${messageId}` : messageId,
        "aria-keyshortcuts": "Control+Enter",
        // 溜めている間は書き換えられない
        readonly: status === "saving",
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

    const message = h({
      tag: "p",
      attrs: { class: status === "idle" ? "send-msg" : `send-msg ${status}`, id: messageId, role: "status" },
      children: resultContent({ status, count, detail, onCopy: () => on.copy(textarea.value) }),
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
      children: [
        target === null
          ? null
          : h({
            tag: "label",
            attrs: { class: "send-label", for: fieldId },
            children: [h({ tag: "span", attrs: { class: "mono" }, children: [target] }), " へのコメント"],
          }),
        target !== null && loc !== null ? locationChip({ loc, id: locId, onUnquote: on.unquote }) : null,
        textarea,
        folded
          ? null
          : h({
            tag: "div",
            attrs: { class: "send-row" },
            children: [
              message,
              h({
                tag: "button",
                attrs: {
                  class: "btn primary",
                  type: "submit",
                  title: "レビューに追加（Ctrl+Enter）",
                  disabled: status === "saving",
                },
                children: [icon("comment"), "レビューに追加"],
              }),
            ],
          }),
      ],
    });
    return form;
  }
}
