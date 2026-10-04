// 回答・意見の送信。詳細パネルと詳細の全画面の下端に留める、開いている項目へ回答・意見を送る入力欄と送るボタン。送った結果を入力の近くに出す。

namespace MindmapPreview {
  /** 送信の状態。idle は結果を出さない */
  export type SendStatus = "idle" | "sending" | "sent" | "empty" | "failed";

  /** 回答・意見の送信の引数 */
  export type SendFormProps = {
    /** 送る先の項目の ID。ラベル「{ID} への回答・意見」に等幅で出す */
    target: string;
    /** 入力欄の中身 */
    body?: string;
    status?: SendStatus;
    /** 受けた日時（サーバーが返した `sent`）。`sent` のとき JST で出す */
    sentAt?: string | null;
    /** サーバーが返した送れなかった理由。`failed` で null なら、サーバーに届かなかったとして立ち上げ直しの案内と「本文を写す」を出す */
    detail?: string | null;
    /** 入力欄の中身が変わったとき */
    onInput: (body: string) => void;
    /** 送るボタンか Ctrl+Enter（macOS は Cmd+Enter）。`sending` の間は呼ばない */
    onSend: (body: string) => void;
    /** 「本文を写す」を押したとき */
    onCopy: (body: string) => void;
  };

  /** 送っている印と文言を出すまでの待ち（ミリ秒）。すぐ終わる送信では点滅させない */
  const SENDING_NOTICE_DELAY_MS = 1000;

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

  /** 結果の要素の中身（状態ごとの印と文言）。送っている間は、待ちの後に印と文言を入れる */
  function resultContent({ status, sentAt, detail, onCopy }: Pick<SendFormProps, "status" | "sentAt" | "detail"> & {
    onCopy: () => void;
  }): Child[] {
    if (status === "sent") {
      return [
        icon("check"),
        h({
          tag: "span",
          children: [`送りました（${sentAt === null || sentAt === undefined ? "" : formatJst(sentAt)}）。次の話し合いの最初に取り込みます。`],
        }),
      ];
    }
    if (status === "empty") {
      return [icon("alert"), h({ tag: "span", children: ["回答・意見を入れてから送ってください。"] })];
    }
    if (status === "failed") {
      // サーバーが理由を返した: 理由を出す
      if (detail !== null && detail !== undefined) {
        return [icon("alert"), h({ tag: "span", children: [`送れませんでした。${detail}`] })];
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
                "送れませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから送ってください。",
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

  /** 項目へ回答・意見を送る入力欄と送るボタン、結果を返す */
  export function sendForm({
    target,
    body = "",
    status = "idle",
    sentAt = null,
    detail = null,
    onInput,
    onSend,
    onCopy,
  }: SendFormProps): HTMLFormElement {
    sendFormSequence += 1;
    const fieldId = `send-${sendFormSequence}`;
    const messageId = `${fieldId}-msg`;

    /** 送っている間は送らない。それ以外は入力欄の中身そのままを渡す */
    const trySend = (): void => {
      if (status === "sending") return;
      onSend(textarea.value);
    };

    const textarea = h({
      tag: "textarea",
      attrs: {
        id: fieldId,
        name: "body",
        rows: 2,
        "aria-describedby": messageId,
        "aria-keyshortcuts": "Control+Enter",
        // 送っている間は書き換えられない
        readonly: status === "sending",
        // 本文が空で送ろうとした: 入力の誤りとして示す
        "aria-invalid": status === "empty" ? "true" : null,
        oninput: () => onInput(textarea.value),
        onkeydown: (event) => {
          const key = event as KeyboardEvent;
          // 変換の確定の Enter では送らない
          if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
            key.preventDefault();
            trySend();
          }
        },
      },
      children: [body],
    });

    const message = h({
      tag: "p",
      attrs: { class: status === "idle" ? "send-msg" : `send-msg ${status}`, id: messageId, role: "status" },
      children: resultContent({ status, sentAt, detail, onCopy: () => onCopy(textarea.value) }),
    });
    // 送っている印と文言は、待ちの後に入れる
    if (status === "sending") {
      window.setTimeout(() => {
        message.replaceChildren(
          h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }),
          h({ tag: "span", children: ["送っています"] }),
        );
      }, SENDING_NOTICE_DELAY_MS);
    }

    return h({
      tag: "form",
      attrs: {
        class: "send send-footer",
        novalidate: true,
        "data-id": target,
        onsubmit: (event) => {
          event.preventDefault();
          trySend();
        },
      },
      children: [
        h({
          tag: "label",
          attrs: { class: "send-label", for: fieldId },
          children: [h({ tag: "span", attrs: { class: "mono" }, children: [target] }), " への回答・意見"],
        }),
        textarea,
        h({
          tag: "div",
          attrs: { class: "send-row" },
          children: [
            message,
            h({
              tag: "button",
              attrs: {
                class: "btn primary",
                type: "submit",
                title: "送る（Ctrl+Enter）",
                disabled: status === "sending",
              },
              children: [icon("send"), "送る"],
            }),
          ],
        }),
      ],
    });
  }
}
