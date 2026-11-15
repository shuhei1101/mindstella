import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { DuplicateIdNotice } from "@/shared/components/duplicate-id-notice";

describe("DuplicateIdNotice", () => {
  // 重なった ID を並べ、リンクと閉じるで知らせる（正常系）
  test("duplicate_id_notice", async () => {
    // 準備
    const onOpen = vi.fn();
    const onClose = vi.fn();
    render(<DuplicateIdNotice ids={[{ id: "D-12", kind: "検討事項" }]} onOpen={onOpen} onClose={onClose} />);
    // 実行
    await userEvent.click(screen.getByRole("link", { name: "D-12" }));
    await userEvent.click(screen.getByRole("button", { name: "閉じる" }));
    // 検証
    expect(screen.getByRole("alert")).toHaveTextContent("同じ ID の項目が 2 件あります");
    expect(onOpen).toHaveBeenCalledWith("D-12");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
