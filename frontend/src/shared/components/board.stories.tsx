// 項目のカードのストーリー
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ItemCard } from "@/shared/components/board";
import { buildIndex, type Item, type MindmapData } from "@/shared/core/records";
import { RECORDS } from "@/testing/msw/handlers";

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
  args: { index, item: task, meta: ["作業"], links: [], selected: false, marks: undefined, comments: {}, edit: null, onOpen: fn() },
} satisfies Meta<typeof ItemCard>;

export default meta;

type Story = StoryObj<typeof meta>;

/** タグを押せるカード。タグを押すと `onSelectTag` だけが呼ばれ、カードのタグ以外の所を押すと `onOpen` が呼ばれる。カードの外枠は div で、ボタンの入れ子は無い */
export const SelectableTags: Story = { args: { onSelectTag: fn() } };

/** 開いている項目のカード。タグを押せるまま、枠と背景で選択中を示す */
export const SelectableTagsSelected: Story = { args: { onSelectTag: fn(), selected: true } };

/** `onSelectTag` を指定しない今のカード。タグを並べない */
export const Default: Story = {};

/** 検討事項（未決定・推奨の案あり）のカードを選べる。右上のチェックボックスを押すと `pick.onChange` だけが呼ばれ、詳細は開かない */
export const Pickable: Story = {
  args: { item: { ...task, id: "D-1", status: "未決定" }, meta: [], pick: { checked: false, disabled: false, label: "D-1 を選ぶ", onChange: fn() } },
};

/** 選んだカード */
export const Picked: Story = {
  args: { item: { ...task, id: "D-1", status: "未決定" }, meta: [], pick: { checked: true, disabled: false, label: "D-1 を選ぶ", onChange: fn() } },
};

/** 推奨の案を持たない検討事項。チェックボックスを押せない */
export const PickDisabled: Story = {
  args: { item: { ...task, id: "D-3", status: "未決定" }, meta: ["推奨の案なし"], pick: { checked: false, disabled: true, label: "D-3 は推奨の案が無いため選べません", onChange: fn() } },
};

/** AI が決めた検討事項。メタ情報の並びに「AI が決定」を出す */
export const DecidedByAi: Story = {
  args: { item: { ...task, id: "D-4", status: "決定済み" }, meta: ["AI が決定"] },
};
