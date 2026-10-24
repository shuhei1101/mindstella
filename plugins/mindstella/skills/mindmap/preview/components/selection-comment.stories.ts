// 選んだ箇所のコメントの入口のストーリー（部品設計『選んだ箇所のコメントの入口』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** 画面の中ほどの、選んだ範囲の矩形（1 行） */
const middle = new DOMRect(120, 160, 220, 22);

const meta = {
  title: "Preview/SelectionComment",
  render: (args) => {
    const pill = MindmapPreview.selectionComment({
      ...args,
      // 画面の大きさと、画面いっぱいの本文のスクロール領域
      area: {
        viewport: { width: window.innerWidth, height: window.innerHeight },
        scroller: new DOMRect(0, 0, window.innerWidth, window.innerHeight),
      },
    });
    const stage = document.createElement("div");
    stage.append(pill);
    return stage;
  },
  args: {
    anchor: { first: middle, last: middle },
    area: { viewport: { width: 1000, height: 800 }, scroller: new DOMRect(0, 0, 1000, 800) },
    on: { press: fn(), close: fn() },
  },
} satisfies Meta<MindmapPreview.SelectionCommentProps>;

export default meta;

type Story = StoryObj<MindmapPreview.SelectionCommentProps>;

/** 選んだ範囲の始まりの上に出す。幅と高さ 32px の丸に印だけ。面は不透明 */
export const Above: Story = {};

/** ホバー。面の色を変え、名前のツールチップを入口の上に出す（入口へマウスを乗せて見る） */
export const Hover: Story = {};

/** キーボードのフォーカス。印の色の輪で、ホバーと見分ける。ホバーと同じ名前のツールチップを出す */
export const Focus: Story = {
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>("button")?.focus();
  },
};

/** 上に収まらない。選んだ範囲の終わりの下に出し、ツールチップは入口の下に出す */
export const Below: Story = {
  args: {
    anchor: { first: new DOMRect(120, 20, 220, 22), last: new DOMRect(120, 50, 160, 22) },
  },
};

/** 幅 390px で選んだ範囲が画面の端に寄る。入口を画面の端から 8px の内側に収め、ツールチップを入口の右端に揃える */
export const Narrow: Story = {
  args: { anchor: { first: new DOMRect(370, 160, 10, 22), last: new DOMRect(370, 190, 10, 22) } },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
