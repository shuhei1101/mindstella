// 左右に並べた本文の差分のストーリー（部品設計『左右に並べた本文の差分.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { SideBySideBodyDiff } from "@/shared/components/side-by-side-body-diff";

const meta = {
  title: "Shared/SideBySideBodyDiff",
  component: SideBySideBodyDiff,
  args: { before: "段落 A\n\n段落 B\n", after: "段落 A\n\n段落 B を書き換えた\n\n段落 C\n" },
} satisfies Meta<typeof SideBySideBodyDiff>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Paragraphs: Story = { args: {} };

export const Rewritten: Story = { args: {"before": "変える前の文です。\n", "after": "変えた後の文です。\n"} };

export const TableAndList: Story = { args: {"before": "- 項目 A\n- 項目 B\n\n| 列 |\n| --- |\n| 1 |\n", "after": "- 項目 A\n- 項目 C\n\n| 列 |\n| --- |\n| 2 |\n"} };

export const Diagram: Story = { args: {"before": "```mermaid\nflowchart LR\n  A-->B\n```\n", "after": "```mermaid\nflowchart LR\n  A-->C\n```\n"} };
