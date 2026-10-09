// 既定の保存の確かめ。ワークスペースの既定として保存する前に、今の既定と保存する値を並べるモーダル。

namespace MindmapPreview {
  /** 見た目と表示する種類の組（今の既定・保存する値） */
  export type DisplayChoice = { look: string; kinds: Set<string> };

  /** 既定の保存の確かめの引数 */
  export type SettingsConfirmProps = {
    /** 今のワークスペースの既定 */
    from: DisplayChoice;
    /** 保存する値 */
    to: DisplayChoice;
    /** 保存している途中か。真のとき 2 つのボタンを押せなくし、Esc でも閉じない */
    busy?: boolean;
    /** 保存できなかった理由と直し方 */
    error?: string | null;
    on: {
      /** 「保存する」を押したとき */
      save: () => void;
      /** 「取り消す」か Esc を押したとき（保存している間は受けない） */
      cancel: () => void;
    };
  };

  /** 表示する種類を、外した種類の名前で書く（全て出すときは「すべて表示」） */
  export function kindsText(kinds: Set<string>): string {
    const hidden = KIND_KEYS.filter((kind) => !kinds.has(kind)).map((kind) => KIND_LABEL[kind]);
    return hidden.length > 0 ? `${hidden.join("・")}を表示しない` : "すべて表示";
  }

  /** 確かめの 1 行。変える項目は今の既定と保存する値を、変えない項目は今の値と「変えない」を出す */
  function confirmRow({ label, from, to }: { label: string; from: string; to: string }): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "sc-row" },
      children: [
        h({ tag: "dt", children: [label] }),
        h({
          tag: "dd",
          children:
            from === to
              ? [
                h({ tag: "span", attrs: { class: "sc-to" }, children: [to] }),
                h({ tag: "span", attrs: { class: "sc-same" }, children: ["変えない"] }),
              ]
              : [
                h({
                  tag: "span",
                  attrs: { class: "sc-from" },
                  children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["今の既定 "] }), from],
                }),
                icon("arrow"),
                h({
                  tag: "span",
                  attrs: { class: "sc-to" },
                  children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["保存する値 "] }), to],
                }),
              ],
        }),
      ],
    });
  }

  /** 既定の保存の確かめを返す。文書に入れた後、呼ぶ側が `showModal()` で開く。最初のフォーカスは「取り消す」 */
  export function settingsConfirm({ from, to, busy = false, error = null, on }: SettingsConfirmProps): HTMLDialogElement {
    const dialog = h({
      tag: "dialog",
      attrs: { class: "confirm sconfirm", "aria-labelledby": "sc-h" },
      children: [
        h({ tag: "h2", attrs: { id: "sc-h" }, children: ["ワークスペースの既定を書き換えますか"] }),
        h({
          tag: "p",
          attrs: { class: "sc-lead" },
          children: ["このワークスペースを開く全員の既定が変わります。表示の設定を自分で変えている人には、変えた項目は当たりません。"],
        }),
        h({
          tag: "dl",
          attrs: { class: "sc-list" },
          children: [
            confirmRow({ label: "ネットワークの見た目", from: lookLabel(from.look), to: lookLabel(to.look) }),
            confirmRow({ label: "表示する種類", from: kindsText(from.kinds), to: kindsText(to.kinds) }),
          ],
        }),
        error === null
          ? null
          : h({
            tag: "div",
            attrs: { class: "sc-error", role: "alert" },
            children: [icon("alert"), h({ tag: "span", children: [error] })],
          }),
        h({
          tag: "div",
          attrs: { class: "cf-row" },
          children: [
            h({
              tag: "button",
              attrs: {
                class: "btn ghost",
                type: "button",
                autofocus: true,
                disabled: busy,
                "data-focus": "cancel",
                onclick: () => on.cancel(),
              },
              children: ["取り消す"],
            }),
            h({
              tag: "button",
              attrs: {
                class: "btn primary",
                type: "button",
                disabled: busy,
                "data-focus": "confirm",
                onclick: () => on.save(),
              },
              children: busy ? [h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), "保存しています"] : ["保存する"],
            }),
          ],
        }),
      ],
    });
    // Esc: 保存している間は閉じず、それ以外は取り消す（ブラウザの既定の閉じ方を止めて、使う側が閉じる）
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      if (!busy) on.cancel();
    });
    return dialog;
  }
}
