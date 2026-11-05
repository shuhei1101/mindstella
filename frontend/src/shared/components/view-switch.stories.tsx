// 表示形式の切り替えのストーリー（部品設計『表示形式の切り替え.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ViewSwitch } from "@/shared/components/view-switch";

const meta = {
  title: "Shared/ViewSwitch",
  component: ViewSwitch,
  args: { views: [], current: "board", onChange: fn() },
} satisfies Meta<typeof ViewSwitch>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Decisions: Story = { args: {"views": [{"key": "map", "label": "マップ"}, {"key": "board", "label": "ボード"}, {"key": "table", "label": "表"}], "current": "map"} };

export const Tasks: Story = { args: {"views": [{"key": "board", "label": "ボード"}, {"key": "table", "label": "表"}], "current": "table"} };

export const Docs: Story = { args: {"views": [{"key": "cards", "label": "カード"}, {"key": "board", "label": "ボード"}, {"key": "table", "label": "表"}], "current": "cards"} };
