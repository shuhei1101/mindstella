// 差分の印のストーリー（部品設計『差分の印.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { DiffMark } from "@/shared/components/diff-mark";

const meta = {
  title: "Shared/DiffMark",
  component: DiffMark,
  args: { kind: "new" },
} satisfies Meta<typeof DiffMark>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 新規。丸や枠で囲まず太い + だけ */
export const New: Story = { args: { kind: "new" } };

/** 変更。丸や枠で囲まず塗った ● だけ。決定済みの状態の印とは色で分かれる */
export const Changed: Story = { args: { kind: "changed" } };

/** 詳細パネルの題の横の新規の札 */
export const NewLabeled: Story = { args: { kind: "new", labeled: true } };

/** 消した。差分の色の赤の太い − だけで、新規・変更と同じ大きさ */
export const Removed: Story = { args: { kind: "removed" } };
