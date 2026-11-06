// 本文の形式の札のストーリー（部品設計『本文の形式の札.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { BodyFormatBadge } from "@/shared/components/body-format-badge";
import { StatusMark } from "@/shared/components/icon";
import { WithdrawnBadge } from "@/shared/components/withdrawn-badge";

const meta = {
  title: "Shared/BodyFormatBadge",
  component: BodyFormatBadge,
  args: { format: "md" },
} satisfies Meta<typeof BodyFormatBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

/** Markdown の資料。地を敷かず、細い枠と `MD` の文字 */
export const Markdown: Story = { args: { format: "md" } };

/** HTML の資料。地の面を敷いた `HTML` の文字 */
export const Html: Story = { args: { format: "html" } };

/** 種類・状態の札（完成）・取り下げの札・納品物の印と並べ、等幅の文字と地で見分けられることを見せる */
export const BesideOtherBadges: Story = {
  args: { format: "html" },
  render: (args) => (
    <div className="flex items-center gap-3">
      <BodyFormatBadge {...args} />
      <span data-status="完成" className="inline-flex items-center gap-1 text-xs">
        <StatusMark status="完成" />
        完成
      </span>
      <WithdrawnBadge />
      {/* 資料のカードの納品物の札と同じ見た目 */}
      <span className="rounded-control bg-mark-weak px-1 text-xs text-mark">納品物</span>
    </div>
  ),
};
