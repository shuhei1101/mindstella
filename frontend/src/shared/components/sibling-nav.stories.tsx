// 一覧の並びの前後の項目へ移るボタンのストーリー（並びの先頭・途中・末尾）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { SiblingNav } from "@/shared/components/sibling-nav";

const meta = {
  title: "Shared/SiblingNav",
  component: SiblingNav,
  args: { position: 2, total: 3, onPrev: fn(), onNext: fn() },
} satisfies Meta<typeof SiblingNav>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 並びの途中。前後のどちらにも移れる */
export const Middle: Story = {};

/** 並びの先頭。前の項目へは移れない */
export const First: Story = { args: { position: 1, total: 2 } };

/** 並びの末尾。次の項目へは移れない */
export const Last: Story = { args: { position: 3, total: 3 } };

/** 4 桁の件数（「1234 / 5678」）。位置の文字を折り返さない */
export const ManyItems: Story = { args: { position: 1234, total: 5678 } };
