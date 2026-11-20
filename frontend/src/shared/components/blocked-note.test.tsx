import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { BlockedNote } from "@/shared/components/blocked-note";

describe("BlockedNote", () => {
  // 溜めた後に AI が書き換えた項目は、取り消してからの再入力を案内する（正常系）
  test("blocked_note_when_changed", () => {
    // 準備
    const blocked = { id: "D-1", reason: "changed" as const, detail: "", refs: [] };
    // 実行
    render(<BlockedNote blocked={blocked} updated="2026-11-20T03:04:00Z" />);
    // 検証
    expect(screen.getByText(/取り消してから再入力してください。$/)).toBeTruthy();
  });
});
