// 選んだ箇所のコメントの入口のストーリー（部品設計『選んだ箇所のコメントの入口.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { SelectionComment } from "@/shared/components/selection-comment";

/** 画面の中ほどの、選んだ範囲の矩形（1 行） */
const middle = new DOMRect(120, 160, 220, 22);

const meta = {
  title: "Shared/SelectionComment",
  component: SelectionComment,
  // 画面の大きさと、画面いっぱいの本文のスクロール領域は、描くときの画面の幅で決める
  render: (args) => <SelectionComment {...args} area={{ viewport: { width: window.innerWidth, height: window.innerHeight }, scroller: new DOMRect(0, 0, window.innerWidth, window.innerHeight) }} />,
  args: { anchor: { first: middle, last: middle }, area: { viewport: { width: 1000, height: 800 }, scroller: new DOMRect(0, 0, 1000, 800) }, onOpen: fn(), onClose: fn() },
} satisfies Meta<typeof SelectionComment>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 選んだ範囲の始まりの上に出す。幅と高さ 32px の丸に印だけ。左端を選んだ範囲の始まりの左端に揃える。面は不透明 */
export const Above: Story = {};

/** ホバー。面の色を変え、名前「選んだ箇所にコメント」のツールチップを選んだ範囲と反対の側（入口の上）に出す。入口とツールチップの間を透明な領域でつなぎ、ツールチップへポインターを動かしても消さない（入口へマウスを乗せて見る） */
export const Hover: Story = {};

/** キーボードのフォーカス。印の色の輪で、ホバーと見分ける。ホバーと同じ名前のツールチップを出す */
export const Focus: Story = {
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>("button")?.focus({ focusVisible: true });
  },
};

/** 上に収まらない（選んだ範囲の始まりが画面の上端の近く）。選んだ範囲の終わりの下に出し、終わりの行の左端に揃える。ツールチップは入口の下に出す */
export const Below: Story = { args: { anchor: { first: new DOMRect(120, 20, 220, 22), last: new DOMRect(120, 50, 160, 22) } } };

/** 幅 390px で選んだ範囲が画面の端に寄る。入口を画面の端から 8px の内側に収める。画面の右半分に出した入口は、ツールチップを入口の右端に揃えて画面の外へはみ出さない */
export const Narrow: Story = {
  args: { anchor: { first: new DOMRect(370, 160, 10, 22), last: new DOMRect(370, 190, 10, 22) } },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
