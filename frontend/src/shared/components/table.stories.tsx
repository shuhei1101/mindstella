// 表のストーリー（部品設計『表.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn, userEvent, within } from "storybook/test";

import { StatusMark } from "@/shared/components/icon";
import { Table, type Row, type TableColumn } from "@/shared/components/table";

/** 確度の並び（並べ替え・絞り込みの値の順） */
const CONFIDENCE_ORDER = ["高", "中", "低"];

/** 表の列の定義 */
const columns: TableColumn[] = [
  { key: "id", label: "ID" },
  { key: "title", label: "タイトル", fixed: true },
  { key: "conf", label: "確度", filterable: true, order: CONFIDENCE_ORDER },
  {
    key: "status",
    label: "状態",
    filterable: true,
    cell: (row) => (
      <span className="inline-flex items-center gap-1">
        <StatusMark status={String(row["status"])} />
        {String(row["status"])}
      </span>
    ),
  },
];

/** 表の行 */
const rows: Row[] = [
  { id: "D-1", title: "プレビューの画面の分け方", conf: "高", status: "決定済み" },
  { id: "D-2", title: "ネットワークで扱う項目の数の上限", conf: "中", status: "未決定" },
  { id: "D-3", title: "資料の状態の値", conf: "高", status: "要見直し" },
  { id: "D-4", title: "デザインスタイルの選び方", conf: "低", status: "保留" },
];

/** 差分の印とコメントの印を付ける行を足した行 */
const markedRows: Row[] = [
  ...rows,
  { id: "D-5", title: "変更履歴に持たせる回数の既定", conf: "中", status: "決定済み" },
  { id: "D-37", title: "差分の表示から抜ける操作の置き場所", conf: "高", status: "未決定" },
];

const meta = {
  title: "Shared/Table",
  component: Table,
  args: { kind: "decisions", columns, rows, onSort: fn(), onFilter: fn(), onPin: fn(), onHiddenColumnsChange: fn(), onResetColumns: fn(), onOpenItem: fn() },
} satisfies Meta<typeof Table>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 通常。並べ替えの印は見出しにホバーかフォーカスしたときだけ出す。チップの行の右端に列のアイコンと「列の表示」のボタンを置き、チップの行と表の間を 12px 空ける */
export const Default: Story = {};

/** タイトルで昇順。向きの矢印を出し、`aria-sort="ascending"` */
export const SortedAsc: Story = { args: { sort: { key: "title", dir: "asc" } } };

/** タイトルで降順。`aria-sort="descending"` */
export const SortedDesc: Story = { args: { sort: { key: "title", dir: "desc" } } };

/** 確度 = 高で絞り込み中。表の上にチップと「すべて解除」を並べる。列の見出しには並べ替えとピン留めだけを置き、絞り込みのボタンを出さない */
export const Filtered: Story = { args: { filters: { conf: ["高"] } } };

/** ID の列までピン留め。押した列のボタンだけが押された見た目で、固定した列の境に影 */
export const Pinned: Story = { args: { pinTo: "id" } };

/** 長いタイトル。タイトルの列は折り返し、ほかの列は崩れない */
export const LongTitle: Story = {
  args: {
    rows: [
      {
        id: "D-5",
        title: "プレビューの画面を、記録の種類ごとにマップ・ボード・カード・表のどれで読み返せるようにするか、狭い幅ではどの列を畳むかを含めて決める",
        conf: "中",
        status: "未決定",
      },
      ...rows,
    ],
  },
};

/** 該当なし（ピン留め中）。表の場所に該当なしと次の操作を書き、横に送っても文言は表の枠の左に留める */
export const NoMatch: Story = { args: { filters: { conf: ["中"] }, pinTo: "id", rows: rows.slice(0, 1) } };

/** 差分の表示の間。変えた行のタイトルの右に ●、足した行に + を置き、印の無い行は変わらない */
export const Marked: Story = { args: { rows: markedRows, marks: { "D-5": "changed", "D-37": "new" } } };

/** コメントを書いた行。タイトルの右に差分の印、その後ろにコメントの印を置き、印の無い行は変わらない */
export const Commented: Story = { args: { rows: markedRows, marks: { "D-5": "changed" }, comments: { "D-5": 1, "D-37": 12 } } };

/** 取り下げた行。タイトルの右に取り下げの札、その後ろに差分の印を置き、行の文字を薄くする。取り下げていない行は変わらない。ホバー・フォーカスの見せ方はほかの行と同じ */
export const Withdrawn: Story = {
  args: { rows: [...rows, { id: "R-1", title: "別の調査で足りた調査", conf: "中", status: "決定済み", withdrawn: true }], marks: { "R-1": "changed" } },
};

/** 列の表示のポップオーバーを開いている。題は「列の表示」。タイトルの列は外せない */
export const ColumnsPopover: Story = {
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "列の表示" }));
  },
};

/** 用語集で、用語に「移し」を含む行に絞っている。表の上に「用語に「移し」を含む」のチップと「すべて解除」を並べる。英数字で終わる列名（ID）は「ID に「G-」を含む」のように空白を挟む。列の見出しに絞り込みのボタンを出さない */
export const TextFiltered: Story = {
  args: {
    kind: "terms",
    columns: [
      { key: "id", label: "ID" },
      { key: "title", label: "用語", fixed: true },
      { key: "meaning", label: "意味" },
      { key: "aliases", label: "別名" },
      { key: "avoid", label: "使わない表記" },
      { key: "tags", label: "タグ", filterable: true },
    ],
    rows: [
      { id: "G-1", title: "移し替え", meaning: "ワークスペースを今の版へ直すこと", aliases: ["マイグレーション"], avoid: [], tags: ["mindstella"] },
      { id: "G-2", title: "ワークスペース", meaning: "話し合いの記録を置くフォルダ", aliases: [], avoid: [], tags: ["mindstella"] },
      { id: "G-3", title: "検討事項", meaning: "決めたいこと", aliases: [], avoid: [], tags: [] },
    ],
    filters: { "~title": ["移し"], "~id": ["G-"] },
  },
};
