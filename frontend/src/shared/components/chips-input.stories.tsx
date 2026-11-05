// チップの入力のストーリー（部品設計『チップの入力.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ChipsInput } from "@/shared/components/chips-input";

const meta = {
  title: "Shared/ChipsInput",
  component: ChipsInput,
  args: { controlId: "chips", name: "タグ", hint: "タグを入れる", values: [], onChange: fn() },
} satisfies Meta<typeof ChipsInput>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = { args: {"values": ["D-1", "T-3"], "monospace": true} };

export const MainToggle: Story = { args: {"values": [{"name": "画面", "main": true}, {"name": "記録の形"}, {"name": "通知"}], "mainToggle": true, "suggestions": ["画面", "記録の形", "通知", "タスク"]} };

export const MainToggleDisabled: Story = { args: {"values": [{"name": "画面", "main": true}, {"name": "記録の形"}], "mainToggle": true, "disabled": true} };

export const MainToggleLongNarrow: Story = { args: {"values": [{"name": "すべての画面の絞り込みとドロワーの並び", "main": true}, {"name": "ゴールと設定"}], "mainToggle": true} };
