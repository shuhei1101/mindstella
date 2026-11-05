// タグの並びのストーリー（部品設計『タグの並び.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { TagList } from "@/shared/components/tag-list";

const meta = {
  title: "Shared/TagList",
  component: TagList,
  args: { values: [] },
} satisfies Meta<typeof TagList>;

export default meta;

type Story = StoryObj<typeof meta>;

export const OneMain: Story = { args: {"values": [{"name": "画面", "main": true}, {"name": "記録の形"}]} };

export const TwoMain: Story = { args: {"values": [{"name": "mindstella"}, {"name": "ゴールと設定", "main": true}, {"name": "画面", "main": true}]} };

export const NoMain: Story = { args: {"values": [{"name": "mindstella"}, {"name": "タスク"}]} };

export const StringTags: Story = { args: {"values": ["通知", "画面"]} };

export const LongNarrow: Story = { args: {"values": [{"name": "すべての画面の絞り込みとドロワーの並び", "main": true}, {"name": "ゴールと設定"}, {"name": "タスク"}]} };
