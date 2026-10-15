// 本文の形式の札のストーリー（部品設計『本文の形式の札』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

const meta = {
  title: "Preview/BodyFormatBadge",
  render: (args) => {
    const stage = document.createElement("div");
    stage.append(MindmapPreview.bodyFormatBadge(args));
    return stage;
  },
  args: { format: "md" },
} satisfies Meta<MindmapPreview.BodyFormatBadgeProps>;

export default meta;

type Story = StoryObj<MindmapPreview.BodyFormatBadgeProps>;

/** Markdown の資料。地を敷かず、細い枠と `MD` の文字 */
export const Markdown: Story = { args: { format: "md" } };

/** HTML の資料。地の面を敷いた `HTML` の文字 */
export const Html: Story = { args: { format: "html" } };

/** 種類・状態の札（完成）・取り下げの札・納品物の印と並べ、等幅の文字と地で見分けられることを見せる */
export const BesideOtherBadges: Story = {
  args: { format: "html" },
  render: (args) => {
    const stage = document.createElement("div");
    stage.style.display = "flex";
    stage.style.alignItems = "center";
    stage.style.gap = "12px";
    stage.append(
      MindmapPreview.bodyFormatBadge(args),
      MindmapPreview.statusBadge("完成"),
      MindmapPreview.withdrawnBadge(),
      MindmapPreview.deliverableBadge(),
    );
    return stage;
  },
};
