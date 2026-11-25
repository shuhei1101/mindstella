import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { RecordText } from "@/shared/components/record-text";
import type { LookupRecordId, RecordIdTarget } from "@/shared/core/record-ids";

/** 見本の記録にある ID と中身（D-99 は記録に無い） */
const TARGETS: Record<string, RecordIdTarget> = {
  "D-1": { id: "D-1", kind: "item", title: "保存先の決め方", kindLabel: "検討事項", status: "未決定" },
  "TH-1": { id: "TH-1", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" },
};

const lookup: LookupRecordId = (id) => TARGETS[id] ?? null;

describe("RecordText", () => {
  // 記録にある ID だけをリンクにし、押すと onOpen を呼ぶ（正常系）
  test("record_text_link", async () => {
    // 準備
    const onOpen = vi.fn();
    const { container } = render(<RecordText text="D-1 の比較（TH-1 の続き、D-99 は除く）" mode="link" lookup={lookup} onOpen={onOpen} />);
    // 実行
    await userEvent.click(screen.getByRole("link", { name: "D-1" }));
    // 検証
    expect(screen.getByRole("link", { name: "D-1" })).toHaveAttribute("href", "#id=D-1");
    expect(screen.getByRole("link", { name: "TH-1" })).toHaveAttribute("href", "#id=TH-1");
    expect(screen.queryByRole("link", { name: "D-99" })).toBeNull();
    expect(container).toHaveTextContent("D-1 の比較（TH-1 の続き、D-99 は除く）");
    expect(onOpen).toHaveBeenCalledWith("D-1");
  });

  // マーカーはフォーカスできる要素にせず、説明を描く（正常系）
  test("record_text_marker", () => {
    // 実行
    const { container } = render(<RecordText text="D-1 の比較（D-99 は除く）" mode="marker" lookup={lookup} descriptionId="ids" />);
    // 検証
    const marker = container.querySelector('[data-record-id="D-1"]');
    expect(marker?.tagName).toBe("SPAN");
    expect(container.querySelector("a, button, [tabindex]")).toBeNull();
    const description = container.querySelector("#ids");
    for (const text of ["保存先の決め方", "D-1", "検討事項", "未決定"]) expect(description).toHaveTextContent(text);
  });

  // 記録にある ID が無いときは文字だけ（正常系）
  test("record_text_no_ids", () => {
    // 実行
    const { container } = render(<RecordText text="保存先の比較" mode="marker" lookup={lookup} descriptionId="ids" />);
    // 検証
    expect(container).toHaveTextContent("保存先の比較");
    expect(container.querySelector("[data-record-id]")).toBeNull();
    expect(container.querySelector("#ids")).toBeNull();
  });
});
