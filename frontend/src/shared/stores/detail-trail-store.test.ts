import { beforeEach, describe, expect, test } from "vitest";

import { useDetailTrailStore } from "@/shared/stores/detail-trail-store";

const visit = (id: string | undefined): void => { useDetailTrailStore.getState().visit(id); };

describe("useDetailTrailStore", () => {
  beforeEach(() => { visit(undefined); });

  // 見てきた項目を行き来する（正常系）
  test("detail_trail", () => {
    // 実行
    visit("D-1");
    visit("D-2");
    visit("D-1");
    // 検証
    expect(useDetailTrailStore.getState()).toMatchObject({ items: ["D-1", "D-2"], position: 0 });
  });

  // 閉じると履歴を空にする（正常系）
  test("detail_trail_when_closed", () => {
    // 実行
    visit("D-1");
    visit(undefined);
    // 検証
    expect(useDetailTrailStore.getState()).toMatchObject({ items: [], position: -1 });
  });
});
