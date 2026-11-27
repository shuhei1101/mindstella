// 項目のカードのストーリー
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ItemCard } from "@/shared/components/board";
import { buildIndex, type Item, type MindmapData } from "@/shared/core/records";
import { RECORDS } from "@/testing/msw/handlers";
import { sampleRecordLookup } from "@/testing/record-lookup";

const index = buildIndex(RECORDS as unknown as MindmapData);

/** タグを 3 つ持つタスク */
const task: Item = {
  id: "T-1",
  title: "絞り込みの条件をタブの保存領域に残す",
  status: "未着手",
  kind: "作業",
  tags: [{ name: "画面", main: true }, { name: "保存" }, { name: "絞り込み" }],
  created: "2026-11-21T00:00:00+00:00",
  updated: "2026-11-21T00:00:00+00:00",
};

const meta = {
  title: "Shared/ItemCard",
  component: ItemCard,
  render: (args) => (
    <div className="w-64">
      <ItemCard {...args} />
    </div>
  ),
  args: { index, lookup: sampleRecordLookup, item: task, meta: ["作業"], links: [], selected: false, marks: undefined, comments: {}, edit: null, onOpen: fn() },
} satisfies Meta<typeof ItemCard>;

export default meta;

type Story = StoryObj<typeof meta>;

/** タグを押せるカード。タグを押すと `onSelectTag` だけが呼ばれ、カードのタグ以外の所を押すと `onOpen` が呼ばれる。カードの外枠は div で、ボタンの入れ子は無い */
export const SelectableTags: Story = { args: { onSelectTag: fn() } };

/** 開いている項目のカード。タグを押せるまま、枠と背景で選択中を示す */
export const SelectableTagsSelected: Story = { args: { onSelectTag: fn(), selected: true } };

/** `onSelectTag` を指定しない今のカード。タグを並べない */
export const Default: Story = {};

/** コメントのある項目のカード。コメントのマーカーをカードの右下に置く */
export const WithComments: Story = { args: { onSelectTag: fn(), comments: { [task.id]: 3 } } };

/** 開いている、コメントのある項目のカード。選択中の枠と背景がほかのカードと見分けられる */
export const SelectedWithComments: Story = { args: { onSelectTag: fn(), comments: { [task.id]: 3 }, selected: true } };

/** 作成の後に更新した項目のカード。種類・状態の文字の行の次に「作成 {日時}・更新 {日時}」を出す */
export const Dates: Story = { args: { item: { ...task, created: "2026-11-02T01:15:00+00:00", updated: "2026-11-20T09:40:00+00:00" } } };

/** 列の幅 240px。日時は「作成 {日時}」と「更新 {日時}」の組ごとに折り返し、カードの外へはみ出さない */
export const DatesNarrow: Story = {
  args: { item: { ...task, created: "2026-11-02T01:15:00+00:00", updated: "2026-11-20T09:40:00+00:00" } },
  render: (args) => (
    <div className="w-60">
      <ItemCard {...args} />
    </div>
  ),
};

/** 関係する項目の D-2 のタイトル「D-1 の見直し」を持つ記録 */
const linkedIndex = buildIndex({ ...RECORDS, decisions: [...RECORDS.decisions, { id: "D-2", title: "D-1 の見直し", status: "決定済み" }] } as unknown as MindmapData);

/** タイトルに記録にある D-1 と記録に無い D-99、関係する項目のタイトルに D-1 を持つカード。D-1 は点線の下線のマーカーにし、乗せるとタイトルと状態のツールチップを出す */
export const TitleIdMarkers: Story = { args: { index: linkedIndex, item: { ...task, title: "D-1 の比較（D-99 は除く）" }, links: ["D-2"] } };

/** お気に入りに登録していないカード。右上に線だけの星を出す */
export const FavoriteOff: Story = { args: { onSelectTag: fn(), favorite: { on: false, onToggle: fn() } } };

/** お気に入りに登録したカード。右上に塗った星を出し、星を押すと `onToggle` だけが呼ばれる */
export const FavoriteOn: Story = { args: { onSelectTag: fn(), favorite: { on: true, onToggle: fn() } } };

/** 長いタイトルのお気に入りのカード。タイトルは星と重ならずに折り返す */
export const FavoriteLongTitle: Story = { args: { favorite: { on: true, onToggle: fn() }, item: { ...task, title: "お気に入りに登録した項目のタイトルが長く、カードの幅の中で何行かに折り返すときの星との重なりを確かめる" } } };
