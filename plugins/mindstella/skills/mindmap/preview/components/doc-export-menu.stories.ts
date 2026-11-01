// 資料のエクスポートのメニューのストーリー（部品設計『資料のエクスポートのメニュー』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/DocExportMenu",
  // 呼ぶ側が開くのと同じく、文書に入れて `showPopover()` で開く
  render: (args) => {
    const stage = document.createElement("div");
    const menu = MindmapPreview.docExportMenu(args);
    // 開いた位置ではなく、ストーリーの流れに置く
    menu.style.position = "static";
    stage.append(menu);
    requestAnimationFrame(() => {
      menu.showPopover();
      menu.querySelector<HTMLElement>(`[${MindmapPreview.DOC_EXPORT_FOCUS_ATTR}]`)?.focus();
    });
    return stage;
  },
  args: { on: { format: fn(), confirm: fn(), back: fn(), retry: fn(), close: fn() } },
} satisfies Meta<MindmapPreview.DocExportMenuProps>;

export default meta;

type Story = StoryObj<MindmapPreview.DocExportMenuProps>;

/** 形式を選ぶ。「HTML でエクスポート」と「Markdown でエクスポート」の行を並べ、行の全体が押せる。フォーカスは「HTML でエクスポート」 */
export const Choose: Story = {};

/** Markdown の警告。警告のアイコンと文の下に「戻る」「エクスポート」。フォーカスは「エクスポート」 */
export const Warn: Story = { args: { view: "warn" } };

/** HTML を組み立てている間。「HTML でエクスポート」の行のアイコンが回る輪になり、説明が「エクスポートしています…」。両方の行は押しても何もせず、「Markdown でエクスポート」の行は薄い */
export const Busy: Story = { args: { view: "busy" } };

/** HTML を組み立てられなかった。何が起きたかの文の下に「戻る」「再試行」。フォーカスは「再試行」 */
export const Error: Story = { args: { view: "error" } };

/** 警告から「戻る」で戻した。形式を選ぶ並びで、フォーカスは「Markdown でエクスポート」 */
export const BackFromWarn: Story = { args: { focus: "md" } };

/** 画面の幅 390px。メニューは画面の幅から左右 8px を引いた幅を超えず、行の説明を折り返す */
export const Narrow: Story = {
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** 画面の幅 390px の警告。警告の文を折り返し、「戻る」「エクスポート」を右端に揃える */
export const WarnNarrow: Story = {
  args: { view: "warn" },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
