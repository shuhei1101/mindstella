// 返信の入力。スレッドの下端に留める、返信をレビュー中に溜める入力欄と「レビューに追加」のボタン。

namespace MindmapPreview {
  /** 返信を溜める状態。idle は結果を出さない */
  export type ReplyStatus = "idle" | "saving" | "saved" | "failed";

  /** 返信の入力の引数 */
  export type ReplyFormProps = {
    /** 返信先のスレッドの ID */
    thread: string;
    /** 入力欄の中身 */
    body?: string;
    status?: ReplyStatus;
    /** 溜めた後のレビュー中の書き込みの件数。`saved` のとき出す */
    count?: number | null;
    /** サーバーが返した溜められなかった理由。`failed` で null なら、サーバーに届かなかったとして立ち上げ直しの案内を出す */
    detail?: string | null;
    on: {
      /** 入力欄の中身が変わったとき */
      input: (body: string) => void;
      /** 「レビューに追加」か Ctrl+Enter（macOS は Cmd+Enter）。スレッドの ID と入力欄の中身 */
      save: (thread: string, body: string) => void;
    };
  };

  /** 入力欄の ID に付ける連番（同じ文書に複数置いても ID が重ならないように） */
  let replyFormSequence = 0;

  /** 結果の要素の中身（状態ごとの印と文言） */
  function replyResult({ status, count, detail }: Pick<ReplyFormProps, "status" | "count" | "detail">): Child[] {
    if (status === "saving") {
      return [h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), h({ tag: "span", children: ["レビューに追加しています"] })];
    }
    if (status === "saved") {
      return [icon("check"), h({ tag: "span", children: [`レビューに追加しました（レビュー中 ${count ?? 0} 件）。`] })];
    }
    if (status === "failed") {
      const reason =
        detail === null || detail === undefined
          ? "サーバーが止まっています。立ち上げ直してから追加してください。"
          : detail;
      return [icon("alert"), h({ tag: "span", children: [`レビューに追加できませんでした。${reason}`] })];
    }
    return [];
  }

  /** 返信をレビュー中に溜める入力欄と「レビューに追加」のボタン、結果を返す */
  export function replyForm({ thread, body = "", status = "idle", count = null, detail = null, on }: ReplyFormProps): HTMLFormElement {
    replyFormSequence += 1;
    const fieldId = `reply-${replyFormSequence}`;
    const messageId = `${fieldId}-msg`;
    const saving = status === "saving";

    /** 空白だけの間と溜めている間は溜めない。それ以外は入力欄の中身そのままを渡す */
    const trySave = (): void => {
      if (saving || textarea.value.trim() === "") return;
      on.save(thread, textarea.value);
    };

    const textarea = h({
      tag: "textarea",
      attrs: {
        id: fieldId,
        name: "body",
        rows: 1,
        maxlength: COMMENT_BODY_MAX_LENGTH,
        "aria-keyshortcuts": "Control+Enter",
        "aria-describedby": messageId,
        // 溜めている間は書き換えられない
        readonly: saving,
        oninput: () => {
          on.input(textarea.value);
          // 入力に合わせて、ボタンを押せるかを合わせる
          submit.disabled = saving || textarea.value.trim() === "";
        },
        onkeydown: (event) => {
          const key = event as KeyboardEvent;
          // 変換の確定の Enter では溜めない
          if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
            key.preventDefault();
            trySave();
          }
          // Esc は入力から外れるだけにする（使う側の「一覧へ戻る」へ伝えない）
          if (key.key === "Escape") {
            key.preventDefault();
            key.stopPropagation();
            textarea.blur();
          }
        },
      },
      children: [body],
    });

    const submit = h({
      tag: "button",
      attrs: {
        class: "btn primary",
        type: "submit",
        title: "レビューに追加（Ctrl+Enter）",
        "data-focus": "reply-send",
        disabled: saving || body.trim() === "",
      },
      children: [icon("comment"), "レビューに追加"],
    });

    return h({
      tag: "form",
      attrs: {
        class: "send send-footer reply",
        novalidate: true,
        onsubmit: (event) => {
          event.preventDefault();
          trySave();
        },
      },
      children: [
        h({ tag: "label", attrs: { class: "send-label", for: fieldId }, children: ["返信"] }),
        textarea,
        h({
          tag: "div",
          attrs: { class: "send-row" },
          children: [
            h({ tag: "p", attrs: { class: status === "idle" ? "send-msg" : `send-msg ${status}`, id: messageId, role: "status" }, children: replyResult({ status, count, detail }) }),
            submit,
          ],
        }),
      ],
    });
  }
}
