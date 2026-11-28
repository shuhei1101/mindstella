// 変更履歴のストーリー（部品設計『変更履歴.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { HistoryDialog } from "@/shared/components/history-dialog";

/** 選べる時点（最新・まだまとめていない変更・まとまりの新しい順。未読のまとまりにマーカー） */
const LATEST = { sel: "", name: "最新", sub: "マーカーと差分を出さずに今の内容だけを読む" };
const POINTS = [
  LATEST,
  { sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: 2 },
  { sel: "V-3", name: "通知の方法の検討事項を足す", sub: "10/04 15:20", count: 2, unread: true },
  { sel: "V-2", name: "フェーズの切り方を見直しに戻す", sub: "10/04 14:45", count: 3, unread: true },
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
  args: { points: POINTS, current: "", onSelect: fn(), onClose: fn(), onMarkAllRead: fn() },
} satisfies Meta<typeof HistoryDialog>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 差分を出していない（「最新」にチェック）。未読のまとまり 2 つにマーカーを付け、「すべて既読にする」を出す */
export const Unread: Story = { args: { current: "" } };

/** 未読のまとまり「通知の方法の検討事項を足す」を選んで既読にした後 */
export const ChangeSetSelected: Story = { args: { current: "V-3", points: POINTS.map((point) => (point.sel === "V-3" ? { ...point, unread: false } : point)) } };

/** 未読が無い。「すべて既読にする」を押せない */
export const AllRead: Story = { args: { points: POINTS.map((point) => ({ ...point, unread: false })) } };

/** まとまりがまだ無い */
export const Empty: Story = { args: { points: POINTS.slice(0, 1) } };

/** まとまりが多い。一覧を縦に送る */
export const Many: Story = {
  args: { points: [LATEST, ...Array.from({ length: 30 }, (_, index) => ({ sel: `V-${String(30 - index)}`, name: `まとまり ${String(30 - index)}`, sub: "10/04 15:20", count: index + 1, unread: index < 12 }))] },
};

/** まだまとめていない変更が無い。その行を出さない */
export const NoPending: Story = { args: { points: POINTS.filter((point) => point.sel !== "pending") } };

/** 長い説明のまとまり。名前を折り返し、日時と件数の列を押し出さない */
export const LongText: Story = {
  args: {
    points: [
      ...POINTS.slice(0, 2),
      { sel: "V-2", unread: true, name: "フェーズの切り方を見直しに戻して、対象とカテゴリーの付け替えをまとめて行い、ゴールまでの残りの項目を数え直した長い説明のまとまり", sub: "10/04 14:45", count: 3 },
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

/** 外部の変更のまとまりがある。名前「ほかのセッションの書き込み」の横に「外部の変更」の札を付ける */
export const External: Story = {
  args: {
    points: POINTS.filter((point) => point.sel !== "pending").map((point) =>
      point.sel === "V-3" ? { sel: "V-3", name: "ほかのセッションの書き込み", sub: "10/04 12:10・書き換えが止んで 1 分後に自動でまとめた", count: 4, external: true } : point,
    ),
  },
};

/** 今回の差分（最後にコメントを送信した時点より後の書き換えの全て）。「最新」の次に並べる */
const TURN = { sel: "turn", name: "今回の差分", sub: "10/04 14:50 にコメントを送信した後の書き換え（まとまり 2 つとまだまとめていない変更）", count: 5 };

/** 「最新」の次に「今回の差分」を並べる。変わった項目の数は、まとまりとまだまとめていない変更を 1 つの差分にした数 */
export const TurnDiff: Story = { args: { points: [LATEST, TURN, ...POINTS.slice(1)] } };

/** 「今回の差分」を選んだ後。チェックを付ける */
export const TurnDiffSelected: Story = { args: { current: "turn", points: [LATEST, TURN, ...POINTS.slice(1)] } };

/** まだコメントを送信していない。最初のまとまりからの書き換えの全てを今回の差分にする */
export const TurnDiffNoWrites: Story = {
  args: { points: [LATEST, { sel: "turn", name: "今回の差分", sub: "まだコメントを送信していないため、最初からの書き換えの全て", count: 14 }, ...POINTS.slice(1)] },
};

/** コメントを送信した直後で、その後の書き換えがまだ無い。変わった項目の数は 0 */
export const TurnDiffNoChanges: Story = {
  args: { points: [LATEST, { sel: "turn", name: "今回の差分", sub: "10/04 15:30 にコメントを送信した後の書き換えはまだありません", count: 0 }, ...POINTS.slice(2)] },
};
