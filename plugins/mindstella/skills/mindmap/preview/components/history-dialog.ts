// 変更履歴のモーダル。差分の表示で比べる時点を、日時・説明・変わった項目の数つきで新しい順に並べ、1 つ選ばせる。

namespace MindmapPreview {
  /** モーダルに並べる時点 1 つ */
  export type HistoryPoint = {
    /** 時点の識別子。空文字列は差分を出さない、`pending`・`since`・まとまりの ID */
    sel: string;
    /** 行の名前。まとまりは `commit` の説明 */
    name: string;
    /** 名前の下の補足（日時・「{日時} より後」・説明） */
    sub: string;
    /** その時点で足した・変えた・消した項目の数（差分を出さない行は持たない） */
    count?: number;
  };

  /** 変更履歴のモーダルの引数 */
  export type HistoryDialogProps = {
    /** 選べる時点。先頭から「差分を出さない」・「まだまとめていない変更」・「前回開いてから」・まとまりを新しい順に */
    points: HistoryPoint[];
    /** 今選んでいる時点の `sel`（差分を出さないときは空文字列） */
    current: string;
    /** 時点を選ぶ（空文字列は差分の表示をやめる）。モーダルは閉じてから呼ぶ */
    onPick: (sel: string) => void;
    /** 閉じたとき（選ばずに閉じたときを含む） */
    onClose: () => void;
  };

  /** 時点の行（押すと選ぶ。選んでいる行にチェックと `aria-current` を付ける） */
  function pointRow({
    point,
    selected,
    onPick,
  }: {
    point: HistoryPoint;
    selected: boolean;
    onPick: (sel: string) => void;
  }): HTMLElement {
    return h({
      tag: "li",
      children: [
        h({
          tag: "button",
          attrs: {
            class: "hist-item",
            type: "button",
            "data-sel": point.sel,
            "aria-current": selected ? "true" : null,
            // 開いたときのフォーカスは、選んでいる行に置く
            autofocus: selected,
            onclick: () => onPick(point.sel),
          },
          children: [
            h({ tag: "span", attrs: { class: "hist-check", "aria-hidden": "true" }, children: [selected ? icon("check") : null] }),
            h({
              tag: "span",
              attrs: { class: "hist-main" },
              children: [
                h({ tag: "span", attrs: { class: "hist-name" }, children: [point.name] }),
                h({ tag: "span", attrs: { class: "hist-sub" }, children: [point.sub] }),
              ],
            }),
            point.count === undefined ? null : h({ tag: "span", attrs: { class: "hist-n mono" }, children: [`${point.count} 件`] }),
          ],
        }),
      ],
    });
  }

  /** 変更履歴のモーダルを返す。文書に入れた後、呼ぶ側が `showModal()` で開く。外側の押下と Esc で閉じる */
  export function historyDialog({ points, current, onPick, onClose }: HistoryDialogProps): HTMLDialogElement {
    const dialog = h({
      tag: "dialog",
      attrs: { class: "hist", "aria-labelledby": "hist-title", closedby: "any" },
      children: [
        h({
          tag: "div",
          attrs: { class: "hist-head" },
          children: [
            h({ tag: "h2", attrs: { id: "hist-title" }, children: ["変更履歴"] }),
            h({
              tag: "button",
              attrs: {
                class: "icon-btn",
                type: "button",
                "data-act": "hist-close",
                "aria-label": "変更履歴を閉じる",
                onclick: () => dialog.close(),
              },
              children: [icon("x")],
            }),
          ],
        }),
        h({
          tag: "ul",
          attrs: { class: "hist-list" },
          children: points.map((point) =>
            pointRow({
              point,
              selected: point.sel === current,
              onPick: (sel) => {
                // 選んだら閉じてから知らせる（使う側が描き直しても、モーダルが残らない）
                dialog.close();
                onPick(sel);
              },
            }),
          ),
        }),
      ],
    });
    // 外側（後ろの幕）を押したときも閉じる（`closedby` が効かない環境のため）
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => {
      dialog.remove();
      onClose();
    });
    return dialog;
  }
}
