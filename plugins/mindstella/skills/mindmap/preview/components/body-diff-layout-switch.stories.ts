// 本文の差分の並べ方の切り替えのストーリー（部品設計『本文の差分の並べ方の切り替え』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

const meta = {
  title: "Preview/BodyDiffLayoutSwitch",
  render: (args) => {
    const stage = document.createElement("div");
    stage.append(MindmapPreview.bodyDiffLayoutSwitch(args));
    return stage;
  },
  args: { layout: "inline", on: { change: () => undefined } },
} satisfies Meta<MindmapPreview.BodyDiffLayoutSwitchProps>;

export default meta;

type Story = StoryObj<MindmapPreview.BodyDiffLayoutSwitchProps>;

/** 既定。「インライン」を押した状態 */
export const Inline: Story = {};

/** 「左右に並べる」を押した状態 */
export const Side: Story = { args: { layout: "side" } };

/** 「インライン」を押したまま、「左右に並べる」にキーボードのフォーカスを置いた。印の色の輪を出す */
export const FocusOnOther: Story = {
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>('button[data-layout="side"]')?.focus({ focusVisible: true });
  },
};
