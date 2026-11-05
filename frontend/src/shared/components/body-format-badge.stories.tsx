// 本文の形式の札のストーリー（部品設計『本文の形式の札.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { BodyFormatBadge } from "@/shared/components/body-format-badge";

const meta = {
  title: "Shared/BodyFormatBadge",
  component: BodyFormatBadge,
  args: { format: "md" },
} satisfies Meta<typeof BodyFormatBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Markdown: Story = { args: {"format": "md"} };

export const Html: Story = { args: {"format": "html"} };

export const BesideOtherBadges: Story = { args: {"format": "html"} };
