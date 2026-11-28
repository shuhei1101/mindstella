import * as jsdiff from "diff";
import { describe, expect, test } from "vitest";

import { buildVersions, changedKinds, diffLineParts, htmlChangedLines, removedOf, resolveDiffPoint, turnSub, unreadChangedIds, unreadSetIds, type DiffPoint } from "@/shared/core/diff";
import type { Changes, Item } from "@/shared/core/records";

const changes: Changes = {
  last_seq: 3,
  sets: [
    { id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 3, added: ["D-2"], changed: ["D-1"], removed: [{ id: "D-3", kind: "decision", title: "削除した" }, { id: "T-1", kind: "task", title: "消したタスク" }] },
    { id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: ["D-1"], changed: [] },
  ],
  pending: { added: [], changed: [] },
};
describe("resolveDiffPoint", () => {
  // まとまりを解決する（正常系）
  test("resolve_diff_point", () => {
    // 実行
    const point = resolveDiffPoint(changes, "V-2");
    // 検証
    expect(point?.added.has("D-2")).toBe(true);
    expect(point?.changed.has("D-1")).toBe(true);
    expect(point?.removed.has("D-3")).toBe(true);
  });

  // 記録に無い（正常系）
  test("resolve_diff_point_when_missing", () => {
    expect(resolveDiffPoint(changes, "V-99")).toBeNull();
  });

  // 空の pending（正常系）
  test("resolve_diff_point_when_pending_empty", () => {
    expect(resolveDiffPoint(changes, "pending")).toBeNull();
  });

  // まとまりの ID でない値は差分を出さない（正常系）
  test("resolve_diff_point_when_not_set_id", () => {
    expect(resolveDiffPoint(changes, "since")).toBeNull();
  });
});

const point = (): DiffPoint => resolveDiffPoint(changes, "V-2") as DiffPoint;

describe("buildVersions", () => {
  // キーと本文を戻す（正常系）
  test("build_versions", () => {
    // 準備
    const item = { id: "D-1", title: "新", status: "未決定", history: [{ seq: 3, at: "2026-11-02T00:00:00+00:00", before: { title: "旧" }, body_diff: [{ line: 1, now: ["今の行"], before: ["前の行"] }] }] } as unknown as Item;
    // 実行
    const versions = buildVersions(item, "今の行\n", point());
    // 検証
    expect(versions.before?.title).toBe("旧");
    expect(versions.beforeBody).toBe("前の行\n");
  });

  // 保持の回数を超えた（正常系）
  test("build_versions_when_dropped", () => {
    // 準備
    const item = { id: "D-1", title: "新", status: "未決定", history: [], history_dropped_seq: 3 } as unknown as Item;
    // 実行
    const versions = buildVersions(item, "", point());
    // 検証
    expect(versions.trimmed).toBe(true);
  });
});

describe("diffLineParts", () => {
  // 足した行と消した行（正常系）
  test("diff_line_parts", () => {
    // 実行
    const parts = diffLineParts("一\n二\n", "一\n三\n", jsdiff);
    // 検証
    expect(parts?.filter((part) => part.kind === "removed").flatMap((part) => part.lines)).toEqual(["二"]);
    expect(parts?.filter((part) => part.kind === "added").flatMap((part) => part.lines)).toEqual(["三"]);
  });
});

describe("htmlChangedLines", () => {
  // 足した行を返す（正常系）
  test("html_changed_lines", () => {
    // 実行
    const lines = htmlChangedLines("<p>一</p>\n", "<p>一</p>\n<p>二</p>\n", jsdiff);
    // 検証
    expect(lines?.added).toEqual([2]);
  });
});

describe("removedOf", () => {
  // 種類で絞る（正常系）
  test("removed_of", () => {
    expect(removedOf({ point: point(), kind: "decisions" }).map((item) => item.id)).toEqual(["D-3"]);
  });
});

describe("changedKinds", () => {
  // 追加・変更・削除した項目の種類を返却する（正常系）
  test("changed_kinds", () => {
    // 準備
    const kindsChanges: Changes = {
      last_seq: 2,
      sets: [{ id: "V-1", at: "2026-11-02T00:00:00+00:00", summary: "1 回目", until_seq: 2, added: ["T-2"], changed: ["D-1"], removed: [{ id: "N-3", kind: "note", title: "消したメモ" }] }],
      pending: { added: [], changed: [] },
    };
    // 実行
    const kinds = changedKinds(resolveDiffPoint(kindsChanges, "V-1"));
    // 検証
    expect([...kinds].sort()).toEqual(["decisions", "notes", "tasks"]);
    expect(kinds.has("research")).toBe(false);
  });

  // 差分を出していなければ空（正常系）
  test("changed_kinds_when_null", () => {
    expect(changedKinds(null).size).toBe(0);
  });
});

describe("unreadSetIds", () => {
  // 既読に無いものだけ（正常系）
  test("unread_set_ids", () => {
    expect(unreadSetIds(["V-3", "V-2", "V-1"], ["V-2", "V-9"])).toEqual(["V-3", "V-1"]);
  });
});

/** 送信より後のまとまり V-3 と、前のまとまり V-2・V-1、まだまとめていない変更 D-4 を持つ変更履歴 */
const turnChanges = (turnSeq: number, pendingAdded: string[]): Changes => ({
  last_seq: 6,
  turn_seq: turnSeq,
  turn_at: turnSeq === 0 ? null : "2026-11-28T05:50:00+00:00",
  sets: [
    { id: "V-3", at: "2026-11-28T06:00:00+00:00", summary: "3 回目", until_seq: 5, added: ["D-3"], changed: [] },
    { id: "V-2", at: "2026-11-28T05:00:00+00:00", summary: "2 回目", until_seq: 3, added: [], changed: ["D-2"] },
    { id: "V-1", at: "2026-11-28T04:00:00+00:00", summary: "1 回目", until_seq: 1, added: [], changed: [] },
  ],
  pending: { added: pendingAdded, changed: [] },
});

describe("resolveDiffPoint の今回の差分", () => {
  // 今回の差分は送信より後のまとまりとまだまとめていない変更を合わせる（正常系）
  test.each([
    { name: "after_turn", changes: turnChanges(3, ["D-4"]), fromSeq: 3, added: ["D-3", "D-4"], changed: [] },
    { name: "before_any_send", changes: turnChanges(0, ["D-4"]), fromSeq: 0, added: ["D-3", "D-4"], changed: ["D-2"] },
    { name: "no_changes_after_send", changes: turnChanges(5, []), fromSeq: 5, added: [], changed: [] },
  ])("resolve_diff_point_when_turn: $name", ({ changes: input, fromSeq, added, changed }) => {
    // 実行
    const point = resolveDiffPoint(input, "turn");
    // 検証
    expect(point).not.toBeNull();
    expect(point?.sel).toBe("turn");
    expect(point?.name).toBe("今回の差分");
    expect(point?.fromSeq).toBe(fromSeq);
    expect(point?.untilSeq).toBeNull();
    expect([...(point?.added ?? [])].sort()).toEqual(added);
    expect([...(point?.changed ?? [])].sort()).toEqual(changed);
    expect(point?.removed.size).toBe(0);
  });
});

describe("turnSub", () => {
  // 送信の有無と数で説明が変わる（正常系）
  test.each([
    { turnAt: "2026-10-04T05:50:00+00:00", count: 3, expected: "10/04 14:50 の送信より後の書き換え" },
    { turnAt: "2026-10-04T05:50:00+00:00", count: 0, expected: "10/04 14:50 の送信より後の書き換えはありません" },
    { turnAt: null, count: 5, expected: "送信の前のため、最初からの書き換え" },
  ])("turn_sub: $expected", ({ turnAt, count, expected }) => {
    expect(turnSub(turnAt, count)).toBe(expected);
  });
});

describe("unreadChangedIds", () => {
  // 未読のまとまりの追加と変更だけ（正常系）
  test("unread_changed_ids", () => {
    // 準備
    const input: Changes = {
      last_seq: 3,
      turn_seq: 0,
      turn_at: null,
      sets: [
        { id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 3, added: ["D-2"], changed: [], removed: [{ id: "D-5", kind: "decision", title: "削除した" }] },
        { id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: [], changed: ["D-1"] },
      ],
      pending: { added: [], changed: [] },
    };
    // 実行
    const ids = unreadChangedIds(input, ["V-2"]);
    // 検証
    expect([...ids]).toEqual(["D-2"]);
  });
});
