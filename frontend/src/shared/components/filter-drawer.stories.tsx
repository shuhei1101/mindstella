// 絞り込みのストーリー（部品設計『絞り込み.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { FilterDrawer } from "@/shared/components/filter-drawer";

const meta = {
  title: "Shared/FilterDrawer",
  component: FilterDrawer,
  args: { groups: [{ key: "status", label: "状態", mark: "status", values: [{ value: "未決定", count: 3 }, { value: "保留", count: 1 }, { value: "決定済み", count: 0 }] }, { key: "tags", label: "タグ", values: [{ value: "プレビュー", count: 2 }] }], selected: {}, total: 12, shown: 12, onToggleValue: fn(), onClearGroup: fn(), onClearAll: fn(), onClose: fn(), onTextChange: fn() },
} satisfies Meta<typeof FilterDrawer>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = { args: {} };

export const Selected: Story = { args: {"selected": {"status": ["要見直し", "未決定", "保留", "未整理"], "tags": ["プレビュー"]}, "total": 36, "shown": 3} };

export const ZeroValue: Story = { args: {} };

export const LongTag: Story = { args: {"groups": [{"key": "tags", "label": "タグ", "values": [{"value": "すべての画面の絞り込みとドロワーの並びを見直す長いタグ", "count": 2}]}]} };

export const KeywordHits: Story = { args: {"groups": [{"key": "status", "label": "状態", "mark": "status", "values": [{"value": "未決定", "count": 3, "hit": 2}]}]} };

export const NoMatch: Story = { args: {"selected": {"kind": ["作業"], "status": ["未着手"]}, "groups": [{"key": "kind", "label": "種類", "values": [{"value": "作業", "count": 0}]}, {"key": "status", "label": "状態", "mark": "status", "values": [{"value": "未着手", "count": 0}]}], "total": 8, "shown": 0} };

export const Narrow: Story = { args: {"narrow": true} };

export const TextConditions: Story = { args: {"selected": {"~title": ["移し"]}, "texts": [{"key": "id", "label": "ID", "value": ""}, {"key": "title", "label": "用語", "value": "移し"}, {"key": "meaning", "label": "意味", "value": ""}], "total": 6, "shown": 1} };
