// コメントの印のストーリー（部品設計『コメントの印.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { CommentMark } from "@/shared/components/comment-mark";

const meta = {
  title: "Shared/CommentMark",
  component: CommentMark,
  args: { count: 1 },
} satisfies Meta<typeof CommentMark>;

export default meta;

type Story = StoryObj<typeof meta>;

export const One: Story = { args: {"count": 1} };

export const TwoDigits: Story = { args: {"count": 12} };

export const Overflow: Story = { args: {"count": 128} };
