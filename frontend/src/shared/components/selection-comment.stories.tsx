// 選んだ箇所のコメントの入口のストーリー（部品設計『選んだ箇所のコメントの入口.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn, userEvent } from "storybook/test";

import { SelectionComment } from "@/shared/components/selection-comment";

/** 選んだ範囲の最初と最後の行の矩形 */
const anchorAt = ({ left, top, width }: { left: number; top: number; width: number }) => ({ first: new DOMRect(left, top, width, 20), last: new DOMRect(left, top + 40, width, 20) });

/** 本文のスクロール領域が画面の全体 */
const areaOf = ({ width, height }: { width: number; height: number }) => ({ viewport: { width, height }, scroller: new DOMRect(0, 0, width, height) });

const meta = {
  title: "Shared/SelectionComment",
  component: SelectionComment,
  args: { anchor: anchorAt({ left: 120, top: 200, width: 240 }), area: areaOf({ width: 1280, height: 800 }), onOpen: fn(), onClose: fn() },
} satisfies Meta<typeof SelectionComment>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 選んだ範囲の始まりの上に出す。幅と高さ 32px の丸に印だけ。左端を選んだ範囲の始まりの左端に揃える。面は不透明 */
export const Above: Story = {};

/** ホバー。面の色を変え、名前「選んだ箇所にコメント」のツールチップを選んだ範囲と反対の側（入口の上）に出す */
export const Hover: Story = {
  play: async ({ canvasElement }) => {
    const button = canvasElement.ownerDocument.querySelector<HTMLElement>('button[aria-label="選んだ箇所にコメント"]');
    if (button !== null) await userEvent.hover(button);
  },
};

/** キーボードのフォーカス。印の色の輪で、ホバーと見分ける。ホバーと同じ名前のツールチップを出す */
export const Focus: Story = {
  play: ({ canvasElement }) => {
    canvasElement.ownerDocument.querySelector<HTMLElement>('button[aria-label="選んだ箇所にコメント"]')?.focus({ focusVisible: true });
  },
};

/** 上に収まらない（選んだ範囲の始まりが画面の上端の近く）。選んだ範囲の終わりの下に出し、終わりの行の左端に揃える。ツールチップは入口の下に出す */
export const Below: Story = { args: { anchor: anchorAt({ left: 120, top: 8, width: 240 }) } };

/** 幅 390px で選んだ範囲が画面の端に寄る。入口を画面の端から 8px の内側に収める */
export const Narrow: Story = {
  args: { anchor: anchorAt({ left: 380, top: 200, width: 10 }), area: areaOf({ width: 390, height: 844 }) },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
