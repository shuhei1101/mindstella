// 変更履歴のストーリー（部品設計『変更履歴.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { HistoryDialog } from "@/shared/components/history-dialog";

const meta = {
  title: "Shared/HistoryDialog",
  component: HistoryDialog,
  args: { points: [{ sel: "", name: "差分を出さない（今の内容）", sub: "印と差分を出さずに今の内容だけを読む" }, { sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: 2 }, { sel: "since", name: "前回開いてから", sub: "10/04 13:05 より後", count: 5 }, { sel: "V-1", name: "フェーズの切り方を見直しに戻す", sub: "10/04 14:45", count: 3 }], current: "since", onSelect: fn(), onClose: fn() },
} satisfies Meta<typeof HistoryDialog>;

export default meta;

type Story = StoryObj<typeof meta>;

export const SinceSelected: Story = { args: {"current": "since"} };

export const Off: Story = { args: {"current": ""} };

export const NoPending: Story = { args: {} };

export const LongName: Story = { args: {} };

export const Narrow: Story = { args: {} };
