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

export const Selected: Story = { args: {"selected": {"status": ["要見直し", "未決定", "保留", "未整理"], "tags": ["プレビュー"]}} };

export const ZeroValue: Story = { args: {} };

export const LongTag: Story = { args: {} };

export const KeywordHits: Story = { args: {} };

export const NoMatch: Story = { args: {"selected": {"kind": ["作業"], "status": ["未着手"]}} };

export const Narrow: Story = { args: {"narrow": true} };

export const TextConditions: Story = { args: {"selected": {"~title": ["移し"]}} };
