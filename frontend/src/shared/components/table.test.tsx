import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { Table, type TableProps } from "@/shared/components/table";

const props = (patch: Partial<TableProps> = {}): TableProps => ({
  kind: "decisions",
  columns: [
    { key: "id", label: "ID", fixed: true },
    { key: "title", label: "タイトル", fixed: true },
    { key: "status", label: "状態" },
  ],
  rows: [{ id: "D-1", title: "題", status: "未決定" }],
  onSort: vi.fn(),
  onFilter: vi.fn(),
  onPin: vi.fn(),
  onHiddenColumnsChange: vi.fn(),
  onResetColumns: vi.fn(),
  onOpenItem: vi.fn(),
  ...patch,
});

describe("Table", () => {
  // 見出しで並べ替える（正常系）
  test("table_when_sort", async () => {
    // 準備
    const onSort = vi.fn();
    render(<Table {...props({ onSort })} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /状態.*並べ替え/ }));
    // 検証
    expect(onSort).toHaveBeenCalledWith("status");
  });

  // 列を隠す（正常系）
  test("table_when_hidden_column", () => {
    // 実行
    render(<Table {...props({ hiddenColumns: ["status"] })} />);
    // 検証
    expect(screen.queryByRole("columnheader", { name: /状態/ })).not.toBeInTheDocument();
  });

  // 列をピン留めする（正常系）
  test("table_when_pin", async () => {
    // 準備
    const onPin = vi.fn();
    render(<Table {...props({ onPin })} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "タイトルまで固定" }));
    // 検証
    expect(onPin).toHaveBeenCalledWith("title");
  });
});
