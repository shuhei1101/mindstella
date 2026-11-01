// 資料のエクスポートのメニュー。詳細パネル・詳細の全画面の見出しの「エクスポート」で開き、形式を選ぶ並び・Markdown の警告・HTML を組み立てている間・組み立てられなかったときを、同じメニューの中身を替えて出す。

namespace MindmapPreview {
  /** メニューの中身 */
  export type DocExportView = "choose" | "warn" | "busy" | "error";

  /** エクスポートの形式 */
  export type DocExportFormat = "html" | "md";

  /** 資料のエクスポートのメニューの引数 */
  export type DocExportMenuProps = {
    /** メニューの中身。`choose` は形式を選ぶ並び、`warn` は Markdown の警告、`busy` は HTML を組み立てている間、`error` は組み立てられなかったとき */
    view?: DocExportView;
    /** 中身を出した時点でフォーカスを置く行（`choose` のとき）。警告は「エクスポート」、エラーは「再試行」に置く */
    focus?: DocExportFormat;
    on: {
      /** 形式の行を押した */
      format: (format: DocExportFormat) => void;
      /** 警告で「エクスポート」を押した */
      confirm: () => void;
      /** 警告かエラーで「戻る」を押した */
      back: () => void;
      /** エラーで「再試行」を押した */
      retry: () => void;
      /** Esc かメニューの外を押して閉じた */
      close: () => void;
    };
  };

  /** メニューが開いたときにフォーカスを置く要素が持つ属性 */
  export const DOC_EXPORT_FOCUS_ATTR = "data-dx-focus";

  /** メニューの見出しの `id` を作る連番 */
  let docExportMenuCounter = 0;

  /** 形式の 1 行（アイコン・名前・説明）。行の全体が押せる */
  function formatRow({
    format,
    iconName,
    name,
    sub,
    disabled,
    busy,
    focused,
    on,
  }: {
    format: DocExportFormat;
    iconName: IconName;
    name: string;
    sub: string;
    disabled: boolean;
    busy: boolean;
    focused: boolean;
    on: DocExportMenuProps["on"];
  }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: busy ? "dx-item dx-busy" : "dx-item",
        type: "button",
        "data-format": format,
        // 処理中は押せなくするが、フォーカスは残す
        "aria-disabled": disabled ? "true" : null,
        [DOC_EXPORT_FOCUS_ATTR]: focused ? "" : null,
        onclick: () => {
          if (!disabled) on.format(format);
        },
      },
      children: [
        icon(iconName),
        h({
          tag: "span",
          attrs: { class: "dx-text" },
          children: [
            h({ tag: "span", attrs: { class: "dx-name" }, children: [name] }),
            h({ tag: "span", attrs: { class: "dx-sub", role: busy ? "status" : null }, children: [sub] }),
          ],
        }),
      ],
    });
  }

  /** 警告・エラーの下に置く「戻る」と右のボタン（右のボタンにフォーカスを置く） */
  function footer({ primary, on }: { primary: { label: string; act: "confirm" | "retry" }; on: DocExportMenuProps["on"] }): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "pop-foot dx-foot" },
      children: [
        h({ tag: "button", attrs: { class: "btn", type: "button", "data-dx-act": "back", onclick: on.back }, children: ["戻る"] }),
        h({
          tag: "button",
          attrs: {
            class: "btn primary",
            type: "button",
            "data-dx-act": primary.act,
            [DOC_EXPORT_FOCUS_ATTR]: "",
            onclick: primary.act === "confirm" ? on.confirm : on.retry,
          },
          children: [primary.label],
        }),
      ],
    });
  }

  /** 資料のエクスポートのメニューを返す。`popover="auto"` の要素で、使う側が文書に入れて `showPopover()` で開く（開閉と、エクスポートの処理は使う側が持つ）。Esc かメニューの外を押して閉じたとき `on.close` を呼ぶ */
  export function docExportMenu({ view = "choose", focus = "html", on }: DocExportMenuProps): HTMLElement {
    docExportMenuCounter += 1;
    const titleId = `doc-export-title-${docExportMenuCounter}`;
    const titles: Record<DocExportView, string> = {
      choose: "エクスポート",
      busy: "エクスポート",
      warn: "Markdown でエクスポートしますか?",
      error: "エクスポートできませんでした",
    };
    let content: HTMLElement[];
    if (view === "choose" || view === "busy") {
      const busy = view === "busy";
      content = [
        h({
          tag: "div",
          attrs: { class: "dx-list", role: "group", "aria-labelledby": titleId },
          children: [
            formatRow({
              format: "html",
              iconName: "code",
              name: "HTML でエクスポート",
              sub: busy ? "エクスポートしています…" : "スタイルと用語のツールチップを含む 1 つのファイル",
              disabled: busy,
              busy,
              focused: busy || focus === "html",
              on,
            }),
            formatRow({
              format: "md",
              iconName: "doc",
              name: "Markdown でエクスポート",
              sub: "本文の Markdown だけ",
              disabled: busy,
              busy: false,
              focused: !busy && focus === "md",
              on,
            }),
          ],
        }),
      ];
    } else if (view === "warn") {
      content = [
        h({
          tag: "div",
          attrs: { class: "dx-warn" },
          children: [icon("alert"), h({ tag: "p", children: ["埋め込んだ HTML・チャート・操作できる部品は含まれず、共通のスタイルも外れます。"] })],
        }),
        footer({ primary: { label: "エクスポート", act: "confirm" }, on }),
      ];
    } else {
      content = [
        h({
          tag: "div",
          attrs: { class: "dx-warn dx-error", role: "alert" },
          children: [
            icon("alert"),
            h({ tag: "p", children: ["mdmark のスタイルとスクリプトを読み込めませんでした。ネットワークにつながっているか確かめて、再試行してください。"] }),
          ],
        }),
        footer({ primary: { label: "再試行", act: "retry" }, on }),
      ];
    }
    const menu = h({
      tag: "div",
      attrs: {
        class: "pop doc-export",
        role: "dialog",
        popover: "auto",
        "aria-labelledby": titleId,
        "aria-busy": view === "busy" ? "true" : null,
      },
      children: [h({ tag: "p", attrs: { class: "pop-title", id: titleId }, children: [titles[view]] }), ...content],
    });
    // Esc かメニューの外を押して閉じたとき
    menu.addEventListener("toggle", (event) => {
      if ((event as ToggleEvent).newState === "closed") on.close();
    });
    return menu;
  }
}
