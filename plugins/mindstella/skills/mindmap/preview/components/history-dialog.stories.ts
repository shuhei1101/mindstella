// 変更履歴のストーリー（部品設計『変更履歴』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** 先頭の「差分を出さない」の行 */
const OFF_POINT: MindmapPreview.HistoryPoint = {
  sel: "",
  name: "差分を出さない（今の内容）",
  sub: "印と差分を出さずに今の内容だけを読む",
};

/** まだまとめていない変更の行 */
const PENDING_POINT: MindmapPreview.HistoryPoint = {
  sel: "pending",
  name: "まだまとめていない変更",
  sub: "AI がまだ区切っていない書き換え",
  count: 2,
};

/** 前回開いてからの行 */
const SINCE_POINT: MindmapPreview.HistoryPoint = {
  sel: "since",
  name: "前回開いてから",
  sub: "10/04 13:05 より後",
  count: 5,
};

/** 書き換えのまとまりの行（新しい順） */
const SET_POINTS: MindmapPreview.HistoryPoint[] = [
  { sel: "V-2", name: "フェーズの切り方を見直しに戻す", sub: "10/04 14:45", count: 3 },
  { sel: "V-1", name: "確度の値を決める", sub: "10/04 11:20", count: 2 },
];

const meta = {
  title: "Preview/HistoryDialog",
  // 呼ぶ側が開くのと同じく、文書に入れて `showModal()` で開く
  render: (args) => {
    const stage = document.createElement("div");
    const dialog = MindmapPreview.historyDialog(args);
    stage.append(dialog);
    requestAnimationFrame(() => dialog.showModal());
    return stage;
  },
  args: {
    points: [OFF_POINT, PENDING_POINT, SINCE_POINT, ...SET_POINTS],
    current: "since",
    onPick: fn(),
    onClose: fn(),
  },
} satisfies Meta<MindmapPreview.HistoryDialogProps>;

export default meta;

type Story = StoryObj<MindmapPreview.HistoryDialogProps>;

/** 「前回開いてから」を選んでいる。先頭から差分を出さない・まだまとめていない変更・前回開いてから・まとまり 2 つ */
export const SinceSelected: Story = { args: { current: "since" } };

/** 差分を出していない。「差分を出さない（今の内容）」にチェック */
export const Off: Story = { args: { current: "" } };

/** まだまとめていない変更が無い。その行を出さない */
export const NoPending: Story = {
  args: { points: [OFF_POINT, SINCE_POINT, ...SET_POINTS], current: "since" },
};

/** 長い説明のまとまり。名前を折り返し、日時と件数の列を押し出さない */
export const LongName: Story = {
  args: {
    points: [
      OFF_POINT,
      SINCE_POINT,
      {
        sel: "V-3",
        name: "プレビューの画面を、記録の種類ごとにマップ・ボード・カード・表のどれで読み返せるようにするか、狭い幅ではどの列を畳むかを決め直して、状態の値と合わせて見直しに戻す",
        sub: "10/04 15:30",
        count: 12,
      },
      ...SET_POINTS,
    ],
    current: "V-3",
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
