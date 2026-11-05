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

export const New: Story = { args: {"kind": "new"} };

export const Changed: Story = { args: {"kind": "changed"} };

export const NewLabeled: Story = { args: {"kind": "new", "labeled": true} };

export const Removed: Story = { args: {"kind": "removed"} };
