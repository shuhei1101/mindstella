// 本文の差分の見せ方の切り替えのストーリー（部品設計『本文の差分の見せ方の切り替え.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { BodyDiffViewSwitch } from "@/shared/components/body-diff-view-switch";

const meta = {
  title: "Shared/BodyDiffViewSwitch",
  component: BodyDiffViewSwitch,
  args: { view: "rendered", onChange: fn() },
} satisfies Meta<typeof BodyDiffViewSwitch>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 既定。「描いた結果」を押した状態 */
export const Rendered: Story = { args: { view: "rendered" } };

/** 「原文の差分」を押した状態 */
export const Source: Story = { args: { view: "source" } };

/** 「描いた結果」を押したまま、「原文の差分」にキーボードのフォーカスを置いた。マーカーの色の輪を出す */
export const FocusOnOther: Story = {
  args: { view: "rendered" },
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>('[data-view="source"]')?.focus({ focusVisible: true });
  },
};
