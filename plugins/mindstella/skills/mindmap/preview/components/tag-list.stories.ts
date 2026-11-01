// タグの並びのストーリー（部品設計『タグの並び』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

/** タグの並びの引数 */
type TagListArgs = { values?: (MindmapPreview.Tag | string)[]; width?: number };

const meta = {
  title: "Preview/TagList",
  // タグを並べる先（資料のカード・詳細パネルのタグの行）と同じく、折り返す行に置く
  render: ({ values, width }) => {
    const stage = document.createElement("div");
    stage.style.cssText = `display:flex;flex-wrap:wrap;gap:4px;width:${width === undefined ? "auto" : `${width}px`}`;
    stage.append(MindmapPreview.tagList(values));
    return stage;
  },
  args: { values: [] },
} satisfies Meta<TagListArgs>;

export default meta;

type Story = StoryObj<TagListArgs>;

/** 主題のタグが 1 つと、主題でないタグが 1 つ */
export const OneMain: Story = { args: { values: [{ name: "画面", main: true }, { name: "記録の形" }] } };

/** 主題のタグが 2 つ。主題を先頭へ寄せず、記録の順のまま並べる */
export const TwoMain: Story = {
  args: { values: [{ name: "mindstella" }, { name: "ゴールと設定", main: true }, { name: "画面", main: true }] },
};

/** 主題のタグが無い。どのタグもマーカーを持たない */
export const NoMain: Story = { args: { values: [{ name: "mindstella" }, { name: "タスク" }] } };

/** スレッドのタグのように名前の文字列の並びを渡したとき。どれも主題でないタグとして出す */
export const StringTags: Story = { args: { values: ["通知", "画面"] } };

/** 幅 320px で長い名前の主題のタグを並べる。収まらないタグは次の行へ回し、マーカーは名前と同じ行に残す */
export const LongNarrow: Story = {
  args: {
    values: [{ name: "すべての画面の絞り込みとドロワーの並び", main: true }, { name: "ゴールと設定" }, { name: "タスク" }],
    width: 320,
  },
};
