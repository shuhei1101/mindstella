// 取り下げの札のストーリー（部品設計『取り下げの札』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

const meta = {
  title: "Preview/WithdrawnBadge",
  render: (args) => {
    const stage = document.createElement("div");
    stage.append(MindmapPreview.withdrawnBadge(args));
    return stage;
  },
  args: {},
} satisfies Meta<MindmapPreview.WithdrawnBadgeProps>;

export default meta;

type Story = StoryObj<MindmapPreview.WithdrawnBadgeProps>;

/** 表の行・カードのタイトルの右に置く大きさ。枠付きの × と「取り下げ」 */
export const Default: Story = {};

/** 詳細パネルの題の右に置く大きさ */
export const Large: Story = { args: { large: true } };

/** 検討事項の状態「取り下げ」・タスクの状態「中止」・資料の状態「完成」の札と並べ、枠の有無で見分けられることを見せる */
export const BesideStatusBadges: Story = {
  render: () => {
    const stage = document.createElement("div");
    stage.style.display = "flex";
    stage.style.alignItems = "center";
    stage.style.gap = "12px";
    for (const status of ["取り下げ", "中止", "完成"]) stage.append(MindmapPreview.statusBadge(status));
    stage.append(MindmapPreview.withdrawnBadge());
    return stage;
  },
};
