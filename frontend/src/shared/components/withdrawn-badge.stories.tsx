// 取り下げの札のストーリー（部品設計『取り下げの札.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { WithdrawnBadge } from "@/shared/components/withdrawn-badge";

const meta = {
  title: "Shared/WithdrawnBadge",
  component: WithdrawnBadge,
  args: {},
} satisfies Meta<typeof WithdrawnBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = { args: {} };

export const Large: Story = { args: {"large": true} };

export const BesideStatusBadges: Story = { args: {} };
