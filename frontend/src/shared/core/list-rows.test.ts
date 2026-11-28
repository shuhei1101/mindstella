import { describe, expect, test } from "vitest";

import { CHANGED_VALUE, changedColumn, drawerGroups, sortRows, type ListColumn } from "@/shared/core/list-rows";

type Row = { id: string; created: string; updated: string };

const COLUMNS: ListColumn<Row>[] = [
  { key: "id", label: "ID", get: (row) => row.id },
  { key: "created", label: "作成日時", get: (row) => row.created },
  { key: "updated", label: "更新日時", get: (row) => row.updated },
];

const ROWS: Row[] = [
  { id: "D-10", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-03T00:00:00+00:00" },
  { id: "D-2", created: "2026-11-02T00:00:00+00:00", updated: "2026-11-05T00:00:00+00:00" },
  { id: "D-1", created: "2026-11-03T00:00:00+00:00", updated: "2026-11-04T00:00:00+00:00" },
];

describe("sortRows", () => {
  // 更新日時の新しい順（正常系）
  test("sort_rows_when_updated_desc", () => {
    // 実行
    const rows = sortRows({ rows: ROWS, columns: COLUMNS, sort: "-updated" });
    // 検証
    expect(rows.map((row) => row.id)).toEqual(["D-2", "D-1", "D-10"]);
  });

  // 連番の数の順（正常系）
  test("sort_rows_when_id", () => {
    // 実行
    const rows = sortRows({ rows: ROWS, columns: COLUMNS, sort: "id" });
    // 検証
    expect(rows.map((row) => row.id)).toEqual(["D-1", "D-2", "D-10"]);
  });
});

describe("changedColumn", () => {
  // 未読の変更がある行だけ値を持つ（正常系）
  test("changed_column", () => {
    // 準備
    const column = changedColumn(new Set(["D-2"]));
    // 実行・検証
    expect(column.key).toBe("changed");
    expect(column.get({ id: "D-2" })).toBe("未読の変更あり");
    expect(column.get({ id: "D-1" })).toBeNull();
  });
});

describe("drawerGroups", () => {
  type StatusRow = { id: string; status: string };
  const statusColumn: ListColumn<StatusRow> = { key: "status", label: "状態", get: (row) => row.status };
  const rows: StatusRow[] = [
    { id: "D-1", status: "未決定" },
    { id: "D-2", status: "決定済み" },
    { id: "D-3", status: "未決定" },
  ];

  // 変更の条件を先頭に並べ、件数が 0 でも残す（正常系）
  test.each([
    { name: "two_unread", ids: ["D-1", "D-2"], count: 2 },
    { name: "no_unread", ids: [], count: 0 },
  ])("drawer_groups_when_changed: $name", ({ ids, count }) => {
    // 準備
    const changed = changedColumn(new Set(ids));
    // 実行
    const groups = drawerGroups({ rows, columns: [statusColumn, changed], conditions: [statusColumn, changed], filters: {} });
    // 検証
    expect(groups[0]?.key).toBe("changed");
    expect(groups[0]?.mark).toBe("change");
    expect(groups[0]?.values).toEqual([{ value: CHANGED_VALUE, count }]);
  });
});
