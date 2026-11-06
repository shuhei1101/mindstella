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

export const LongTitle: Story = { args: {"rows": [{"id": "D-5", "title": "とても長いタイトルが折り返されて他の列を崩さないことを確かめるための、説明の多い検討事項の題名", "conf": "高"}]} };

export const NoMatch: Story = { args: {"filters": {"conf": ["中"]}, "pinTo": "id", "rows": []} };

export const ColumnsPopover: Story = { args: {} };

export const Marked: Story = { args: {"marks": {"D-5": "changed", "D-37": "new"}} };

export const TextFiltered: Story = { args: {"kind": "terms", "filters": {"~title": ["移し"]}, "columns": [{"key": "id", "label": "ID"}, {"key": "title", "label": "用語", "fixed": true}, {"key": "meaning", "label": "意味"}], "rows": [{"id": "G-1", "title": "移し替え", "meaning": "版を上げる"}]} };

export const Commented: Story = { args: {"marks": {"D-5": "changed"}, "comments": {"D-5": 1, "D-37": 12}} };

export const Withdrawn: Story = { args: {"marks": {"R-1": "changed"}, "rows": [{"id": "R-1", "title": "取り下げた調査", "conf": "高", "withdrawn": true}, {"id": "R-2", "title": "今の調査", "conf": "低"}]} };
