import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ThreadTitle } from "@/shared/components/thread-title";
import type { LookupRecordId, RecordIdTarget } from "@/shared/core/record-ids";

/** 見本の記録にある ID と中身（D-99 は記録に無い） */
const TARGETS: Record<string, RecordIdTarget> = {
  "D-1": { id: "D-1", kind: "item", title: "保存先の決め方", kindLabel: "検討事項", status: "未決定" },
  "TH-1": { id: "TH-1", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" },
};

const lookup: LookupRecordId = (id) => TARGETS[id] ?? null;

describe("ThreadTitle", () => {
  // タイトルの中の記録にある ID をリンクにする（正常系）
  test("thread_title_id_links", () => {
    // 実行
    const { container } = render(<ThreadTitle title="D-1 の決め方（TH-1 の続き、D-99 は除く）" collapsed={false} lookup={lookup} />);
    // 検証
    expect(container.querySelector('a[data-record-id="D-1"]')).not.toBeNull();
    expect(container.querySelector('a[data-record-id="TH-1"]')).not.toBeNull();
    expect(container.querySelector('[data-record-id="D-99"]')).toBeNull();
    expect(container).toHaveTextContent("D-1 の決め方（TH-1 の続き、D-99 は除く）");
  });

  // 1 行にしたときだけ title を持つ（正常系）
  test.each([
    { collapsed: true, expected: true },
    { collapsed: false, expected: false },
  ])("thread_title", ({ collapsed, expected }) => {
    // 実行
    render(<ThreadTitle title="案の選び方を決めるスレッド" collapsed={collapsed} lookup={lookup} />);
    // 検証
    const title = screen.getByText("案の選び方を決めるスレッド");
    if (expected) {
      expect(title).toHaveAttribute("title", "案の選び方を決めるスレッド");
      expect(title).toHaveAttribute("data-collapsed");
    } else {
      expect(title).not.toHaveAttribute("title");
      expect(title).not.toHaveAttribute("data-collapsed");
    }
  });
});
