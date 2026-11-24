import { describe, expect, test } from "vitest";

import { sortRows, type ListColumn } from "@/shared/core/list-rows";

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
