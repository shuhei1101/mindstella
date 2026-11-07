import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ReviewBodyFold } from "@/shared/components/review-body-fold";

/** 描いた本文の高さを、行の高さ × 行数として返す */
const stubHeight = (lines: number) => {
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(lines * 20);
  const original = window.getComputedStyle.bind(window);
  // 行の高さだけを差し替え、ほかの値は元の計算を返す（Testing Library が名前の計算に使う）
  vi.spyOn(window, "getComputedStyle").mockImplementation((element) => new Proxy(original(element), {
      get: (target, key) => {
        if (key === "lineHeight") return "20px";
        const value: unknown = Reflect.get(target, key);
        return typeof value === "function" ? (value as (...args: unknown[]) => unknown).bind(target) : value;
      },
    }));
};

afterEach(() => {
  vi.restoreAllMocks();
});

const renderFold = (body: string) =>
  render(
    <ReviewBodyFold id="C-1" label="D-1 へのコメント" body={body} open={false} onToggle={vi.fn()}>
      {(content, toggle) => (
        <div>
          {content}
          {toggle ?? <span>開閉なし</span>}
        </div>
      )}
    </ReviewBodyFold>,
  );

describe("ReviewBodyFold", () => {
  // 長い本文を畳む（正常系）
  test("review_body_fold", async () => {
    // 準備
    stubHeight(6);
    // 実行
    renderFold("一\n二\n三\n四\n五\n六");
    // 検証
    const toggle = await screen.findByRole("button", { name: "D-1 へのコメントの続きを読む" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  // 短い本文（正常系）
  test("review_body_fold_when_short", async () => {
    // 準備
    stubHeight(2);
    // 実行
    renderFold("一\n二");
    // 検証
    expect(await screen.findByText("開閉なし")).toBeInTheDocument();
  });
});
