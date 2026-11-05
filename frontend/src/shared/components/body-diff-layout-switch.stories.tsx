// 本文の差分の並べ方の切り替えのストーリー（部品設計『本文の差分の並べ方の切り替え.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { BodyDiffLayoutSwitch } from "@/shared/components/body-diff-layout-switch";

const meta = {
  title: "Shared/BodyDiffLayoutSwitch",
  component: BodyDiffLayoutSwitch,
  args: { layout: "inline", onChange: fn() },
} satisfies Meta<typeof BodyDiffLayoutSwitch>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Inline: Story = { args: {"layout": "inline"} };

export const Side: Story = { args: {"layout": "side"} };

export const FocusOnOther: Story = { args: {"layout": "inline"} };
