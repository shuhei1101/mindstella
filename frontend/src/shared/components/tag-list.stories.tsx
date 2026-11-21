// タグの並びのストーリー（部品設計『タグの並び.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { TagList } from "@/shared/components/tag-list";

const meta = {
  title: "Shared/TagList",
  component: TagList,
  render: (args) => (
    <div data-tags className="flex flex-wrap gap-1">
      <TagList {...args} />
    </div>
  ),
  args: { values: [] },
} satisfies Meta<typeof TagList>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 主題のタグが 1 つと、主題でないタグが 1 つ */
export const OneMain: Story = { args: { values: [{ name: "画面", main: true }, { name: "記録の形" }] } };

/** 主題のタグが 2 つ。主題を先頭へ寄せず、記録の順のまま並べる */
export const TwoMain: Story = { args: { values: [{ name: "mindstella" }, { name: "ゴールと設定", main: true }, { name: "画面", main: true }] } };

/** 主題のタグが無い。どのタグもマーカーを持たない */
export const NoMain: Story = { args: { values: [{ name: "mindstella" }, { name: "タスク" }] } };

/** スレッドのタグのように名前の文字列の並びを渡したとき。どれも主題でないタグとして出す */
export const StringTags: Story = { args: { values: ["通知", "画面"] } };

/** 幅 320px で長い名前の主題のタグを並べる。収まらないタグは次の行へ回し、マーカーは名前と同じ行に残す */
export const LongNarrow: Story = {
  args: { values: [{ name: "すべての画面の絞り込みとドロワーの並び", main: true }, { name: "ゴールと設定" }, { name: "タスク" }] },
  render: (args) => (
    <div data-tags className="flex w-80 flex-wrap gap-1">
      <TagList {...args} />
    </div>
  ),
};

/** 押して絞り込みに加えられるタグ。各タグはボタンで、ホバーで枠と文字を濃くし、読み上げ名は「タグ「{名前}」で絞り込む」。押せる範囲は見た目の上下へ 3px ずつ広げた高さ 24px で、幅 160px で折り返した行の間は 6px */
export const Selectable: Story = {
  args: { values: [{ name: "画面", main: true }, { name: "記録の形" }, { name: "絞り込み" }, { name: "スクロール位置" }], onSelect: fn() },
  render: (args) => (
    <div data-tags className="flex w-40 flex-wrap gap-x-1 gap-y-1.5">
      <TagList {...args} />
    </div>
  ),
};
