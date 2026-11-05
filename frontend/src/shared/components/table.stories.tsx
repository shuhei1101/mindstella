// 表のストーリー（部品設計『表.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { Table } from "@/shared/components/table";

const meta = {
  title: "Shared/Table",
  component: Table,
  args: { kind: "decisions", columns: [{ key: "id", label: "ID" }, { key: "title", label: "タイトル", fixed: true }, { key: "conf", label: "確度", filterable: true }], rows: [{ id: "D-5", title: "記録の形を決める", conf: "高" }, { id: "D-37", title: "画面の幅を決める", conf: "低" }], onSort: fn(), onFilter: fn(), onPin: fn(), onHiddenColumnsChange: fn(), onResetColumns: fn(), onOpenItem: fn() },
} satisfies Meta<typeof Table>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = { args: {} };

export const SortedAsc: Story = { args: {"sort": {"key": "title", "dir": "asc"}} };

export const SortedDesc: Story = { args: {"sort": {"key": "title", "dir": "desc"}} };

export const Filtered: Story = { args: {"filters": {"conf": ["高"]}} };

export const Pinned: Story = { args: {"pinTo": "id"} };

export const LongTitle: Story = { args: {} };

export const NoMatch: Story = { args: {"filters": {"conf": ["中"]}, "pinTo": "id"} };

export const ColumnsPopover: Story = { args: {} };

export const Marked: Story = { args: {"marks": {"D-5": "changed", "D-37": "new"}} };

export const TextFiltered: Story = { args: {"kind": "terms", "filters": {"~title": ["移し"]}} };

export const Commented: Story = { args: {"marks": {"D-5": "changed"}, "comments": {"D-5": 1, "D-37": 12}} };

export const Withdrawn: Story = { args: {"marks": {"R-1": "changed"}} };
