// AI の通知のスレッドに並んだ検討事項の一覧のストーリー
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { DecisionPickList, type DecisionPickRow } from "@/shared/components/decision-pick-list";

const ROWS: DecisionPickRow[] = [
  { id: "D-2", title: "通知に含める内容", status: "未決定", recommended: "A", decidedBy: null },
  { id: "D-3", title: "通知を送信する時機", status: "未決定", recommended: "B", decidedBy: null },
  { id: "D-5", title: "通知の文面の言語", status: "未決定", recommended: null, decidedBy: null },
  { id: "D-1", title: "再送の回数", status: "決定済み", recommended: "A", decidedBy: "ai" },
];

const meta = {
  title: "Shared/DecisionPickList",
  component: DecisionPickList,
  render: (args) => (
    <div className="w-96 max-w-full">
      <DecisionPickList {...args} />
    </div>
  ),
  args: { rows: ROWS, picked: [], onToggle: fn(), onDecide: fn(), onClear: fn() },
} satisfies Meta<typeof DecisionPickList>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 何も選んでいない。推奨の案を持たない D-5 と、AI が決めた決定済みの D-1 は選べない */
export const Default: Story = {};

/** D-2・D-3 を選んでいる。下に選んだ件数と「推奨の案で決定」を出す */
export const Picked: Story = { args: { picked: ["D-2", "D-3"] } };

/** 決定している間。チェックボックスもボタンも押せない */
export const Pending: Story = { args: { picked: ["D-2", "D-3"], pending: true } };

/** 決定できない検討事項があった。記録を取り直した後で D-3 は AI が決定済みにしており、選択を残して理由を出す */
export const Failed: Story = {
  args: {
    rows: ROWS.map((row) => (row.id === "D-3" ? { ...row, status: "決定済み", decidedBy: "ai" } : row)),
    picked: ["D-2", "D-3"],
    failures: [{ id: "D-3", reason: "未決定ではありません（決定済み）" }],
  },
};

/** まとめて決定した後。D-2・D-3 は決定済みで選べない */
export const Decided: Story = {
  args: {
    rows: ROWS.map((row) => (row.id === "D-2" || row.id === "D-3" ? { ...row, status: "決定済み", decidedBy: "user" } : row)),
  },
};
