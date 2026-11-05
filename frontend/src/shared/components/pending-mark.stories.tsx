// 保存待ちの印のストーリー（部品設計『保存待ちの印.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { PendingMark } from "@/shared/components/pending-mark";

const meta = {
  title: "Shared/PendingMark",
  component: PendingMark,
  args: { kind: "pending" },
} satisfies Meta<typeof PendingMark>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Pending: Story = { args: {"kind": "pending"} };

export const Remove: Story = { args: {"kind": "remove"} };

export const Blocked: Story = { args: {"kind": "blocked"} };

export const PendingCompact: Story = { args: {"kind": "pending", "compact": true} };

export const RemoveCompact: Story = { args: {"kind": "remove", "compact": true} };

export const BlockedCompact: Story = { args: {"kind": "blocked", "compact": true} };

export const Dark: Story = { args: {"kind": "pending"} };
