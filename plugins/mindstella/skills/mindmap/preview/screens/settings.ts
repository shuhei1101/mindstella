// 表示の設定。見ている画面に重ねて左から出すパネルに表示の設定の中身を入れ、既定が変わったときは画面の下に知らせを出す。

namespace MindmapPreview {
  /** 表示の設定のパネルの引数 */
  export type SettingsDrawerProps = {
    /** 表示の設定の中身の引数（`on.close` を見出しの × にもつなぐ） */
    panel: SettingsPanelProps;
  };

  /** 既定が変わった知らせの文言 */
  const NOTICE_TEXT = "ワークスペースの既定が変わりました。";

  /** 出している知らせと、消すタイマー（続けて呼ばれたら前のものを消して出し直す） */
  let currentNotice: { element: HTMLElement; timer: number } | null = null;

  /** 表示の設定のパネル（見出しの帯と ×、中身）を返す。開閉は使う側が `open` のクラスで決める */
  export function settingsDrawer({ panel }: SettingsDrawerProps): HTMLElement {
    return h({
      tag: "aside",
      attrs: { class: "settings-drawer", id: "sdrawer", "aria-label": "表示の設定" },
      children: [
        h({
          tag: "div",
          attrs: { class: "comments-head" },
          children: [
            h({ tag: "h2", children: ["表示の設定"] }),
            h({
              tag: "button",
              attrs: {
                class: "icon-btn",
                type: "button",
                "aria-label": "表示の設定を閉じる",
                "data-focus": "close",
                onclick: () => panel.on.close(),
              },
              children: [icon("x")],
            }),
          ],
        }),
        settingsPanel(panel),
      ],
    });
  }

  /** 画面の下に「ワークスペースの既定が変わりました。」を `role="status"` で出し、`durationMs` 経ったら消す */
  export function settingsNotice({ durationMs }: { durationMs: number }): HTMLElement {
    // 続けて呼ばれた: 前の知らせを消して出し直す
    if (currentNotice !== null) {
      window.clearTimeout(currentNotice.timer);
      currentNotice.element.remove();
    }
    const element = h({
      tag: "div",
      attrs: { class: "stoast", role: "status" },
      children: [icon("sliders"), h({ tag: "span", children: [NOTICE_TEXT] })],
    });
    document.body.append(element);
    // 次のコマで出し、すべり込ませる
    requestAnimationFrame(() => element.classList.add("show"));
    const timer = window.setTimeout(() => {
      element.remove();
      if (currentNotice?.element === element) currentNotice = null;
    }, durationMs);
    currentNotice = { element, timer };
    return element;
  }
}
