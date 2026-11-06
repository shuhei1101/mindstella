// 変更履歴のストーリー（部品設計『変更履歴.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { HistoryDialog } from "@/shared/components/history-dialog";

/** 選べる時点（差分を出さない・まだまとめていない変更・前回開いてから・まとまり 2 つ） */
const POINTS = [
  { sel: "", name: "差分を出さない（今の内容）", sub: "印と差分を出さずに今の内容だけを読む" },
  { sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: 2 },
  { sel: "since", name: "前回開いてから", sub: "10/04 13:05 より後", count: 5 },
  { sel: "V-2", name: "フェーズの切り方を見直しに戻す", sub: "10/04 14:45", count: 3 },
  { sel: "V-1", name: "検討事項の初めの並び", sub: "10/03 09:12", count: 12 },
];

const meta = {
  title: "Shared/HistoryDialog",
  component: HistoryDialog,
  // モーダルは文書の末尾に描くので、ストーリーの根に入れ物を置く
  decorators: [
    (Story) => (
      <div>
        <Story />
      </div>
    ),
  ],
  args: { points: POINTS, current: "since", onSelect: fn(), onClose: fn() },
} satisfies Meta<typeof HistoryDialog>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 「前回開いてから」を選んでいる。先頭から差分を出さない・まだまとめていない変更・前回開いてから・まとまり 2 つ */
export const SinceSelected: Story = { args: { current: "since" } };

/** 差分を出していない。「差分を出さない（今の内容）」にチェック */
export const Off: Story = { args: { current: "" } };

/** まだまとめていない変更が無い。その行を出さない */
export const NoPending: Story = { args: { points: POINTS.filter((point) => point.sel !== "pending") } };

/** 長い説明のまとまり。名前を折り返し、日時と件数の列を押し出さない */
export const LongName: Story = {
  args: {
    points: [
      ...POINTS.slice(0, 3),
      { sel: "V-2", name: "フェーズの切り方を見直しに戻して、対象とカテゴリーの付け替えをまとめて行い、ゴールまでの残りの項目を数え直した長い説明のまとまり", sub: "10/04 14:45", count: 3 },
    ],
  },
};

/** 幅 390px。モーダルを画面幅に合わせ、一覧を縦に送る */
export const Narrow: Story = {
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
