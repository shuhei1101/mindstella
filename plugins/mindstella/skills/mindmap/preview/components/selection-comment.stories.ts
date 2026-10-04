// 選んだ箇所のコメントの入口のストーリー（部品設計『選んだ箇所のコメントの入口』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** 画面の中ほどの、選んだ範囲の矩形（1 行） */
const middle = new DOMRect(120, 160, 220, 22);

const meta = {
  title: "Preview/SelectionComment",
  render: (args) => {
    const pill = MindmapPreview.selectionComment(args);
    const stage = document.createElement("div");
    stage.append(pill);
    return stage;
  },
  args: {
    anchor: { first: middle, last: middle },
    on: { press: fn(), close: fn() },
  },
} satisfies Meta<MindmapPreview.SelectionCommentProps>;

export default meta;

type Story = StoryObj<MindmapPreview.SelectionCommentProps>;

/** 選んだ範囲の終わりの下に出す。角を丸め切った横長の形（ピル）に、印と「コメント」 */
export const Below: Story = { args: { placement: "below" } };

/** ホバー。面の色だけを変える（入口へマウスを乗せて見る） */
export const Hover: Story = {};

/** キーボードのフォーカス。印の色の輪で、ホバーと見分ける */
export const Focus: Story = {
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>("button")?.focus();
  },
};

/** 下に収まらない。選んだ範囲の始まりの上に出す */
export const Above: Story = {
  args: {
    anchor: {
      first: new DOMRect(120, window.innerHeight - 70, 220, 22),
      last: new DOMRect(120, window.innerHeight - 24, 160, 22),
    },
    placement: "above",
  },
};

/** 幅 390px で選んだ範囲が画面の端に寄る。入口を画面の端から 8px の内側に収める */
export const Narrow: Story = {
  args: { anchor: { first: new DOMRect(300, 160, 80, 22), last: new DOMRect(300, 190, 80, 22) } },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
