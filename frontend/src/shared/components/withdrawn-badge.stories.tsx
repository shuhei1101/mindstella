// 取り下げの札のストーリー（部品設計『取り下げの札.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { StatusMark } from "@/shared/components/icon";
import { WithdrawnBadge } from "@/shared/components/withdrawn-badge";

const meta = {
  title: "Shared/WithdrawnBadge",
  component: WithdrawnBadge,
  args: {},
} satisfies Meta<typeof WithdrawnBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 表の行・カードのタイトルの右に置く大きさ。枠付きの × と「取り下げ」 */
export const Default: Story = {};

/** 詳細パネルの題の右に置く大きさ */
export const Large: Story = { args: { large: true } };

/** 検討事項の状態「取り下げ」・タスクの状態「中止」・資料の状態「完成」の札と並べ、枠の有無で見分けられることを見せる */
export const BesideStatusBadges: Story = {
  render: () => (
    <div className="flex items-center gap-3">
      {["取り下げ", "中止", "完成"].map((status) => (
        <span key={status} data-status={status} className="inline-flex items-center gap-1 text-xs">
          <StatusMark status={status} />
          {status}
        </span>
      ))}
      <WithdrawnBadge />
    </div>
  ),
};
