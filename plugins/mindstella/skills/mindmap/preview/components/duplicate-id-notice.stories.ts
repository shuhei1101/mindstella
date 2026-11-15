// 重なった ID の通知のストーリー（部品設計『重なった ID の通知』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/DuplicateIdNotice",
  render: (args) => {
    const stage = document.createElement("div");
    const notice = MindmapPreview.duplicateIdNotice(args);
    if (notice !== null) stage.append(notice);
    return stage;
  },
  args: {
    ids: [{ id: "D-12", kind: "検討事項" }],
    onOpen: fn(),
    onClose: fn(),
  },
} satisfies Meta<MindmapPreview.DuplicateIdNoticeProps>;

export default meta;

type Story = StoryObj<MindmapPreview.DuplicateIdNoticeProps>;

/** 重なった ID が 1 件。見出し「同じ ID の項目が 2 件あります」と、片方の ID を変更する案内 */
export const Single: Story = {};

/** 重なった ID が 3 件。ID のリンクを `、` で並べ、折り返す */
export const Multiple: Story = {
  args: {
    ids: [
      { id: "D-12", kind: "検討事項" },
      { id: "T-3", kind: "タスク" },
      { id: "N-8", kind: "メモ" },
    ],
  },
};

/** 幅 390px。本文を折り返し、閉じるボタンを右上に残す */
export const Narrow: Story = {
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
