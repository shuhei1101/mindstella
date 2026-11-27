import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";

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
    const part = title.closest('[data-part="thread-title"]');
    if (expected) {
      expect(title).toHaveAttribute("title", "案の選び方を決めるスレッド");
      expect(part).toHaveAttribute("data-collapsed");
    } else {
      expect(title).not.toHaveAttribute("title");
      expect(part).not.toHaveAttribute("data-collapsed");
    }
  });
});

/** タイトルの要素の行の高さを 20px、全文の高さを `height` にし、ResizeObserver を何もしない実装に差し替える */
const stubTitleHeight = (height: number): void => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe = (): void => undefined;
      disconnect = (): void => undefined;
    },
  );
  const computed = window.getComputedStyle.bind(window);
  vi.spyOn(window, "getComputedStyle").mockImplementation((element, pseudo) => {
    const style = computed(element, pseudo);
    return new Proxy(style, { get: (target, key) => (key === "lineHeight" ? "20px" : Reflect.get(target, key, target) as unknown) });
  });
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(height);
};

describe("ThreadTitle の 2 行の省略", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  // 2 行を超えるときだけ省略して開閉のボタンを出す（正常系）
  test.each([
    { height: 120, expected: true },
    { height: 40, expected: false },
  ])("thread_title_when_clamped（$height）", async ({ height, expected }) => {
    // 準備
    stubTitleHeight(height);
    // 実行
    const { container } = render(<ThreadTitle title="長文の書き込みで始めたスレッドのタイトル" collapsed={false} lookup={lookup} />);
    // 検証
    const part = container.querySelector('[data-part="thread-title"]');
    if (expected) {
      const button = await screen.findByRole("button", { name: "タイトルの続きを表示" });
      expect(part).toHaveAttribute("data-clamped");
      expect(button).toHaveAttribute("aria-expanded", "false");
      expect(document.getElementById(button.getAttribute("aria-controls") ?? "")).toHaveTextContent("長文の書き込みで始めたスレッドのタイトル");
    } else {
      await new Promise((resolve) => requestAnimationFrame(resolve));
      expect(part).not.toHaveAttribute("data-clamped");
      expect(screen.queryByRole("button")).toBeNull();
    }
  });

  // 開閉のボタンで全文を開き、もう一度押すと省略に戻す（正常系）
  test("thread_title_when_toggled", async () => {
    // 準備
    stubTitleHeight(120);
    const { container } = render(<ThreadTitle title="長文の書き込みで始めたスレッドのタイトル" collapsed={false} lookup={lookup} />);
    const part = container.querySelector('[data-part="thread-title"]');
    // 実行（開く）
    await userEvent.click(await screen.findByRole("button", { name: "タイトルの続きを表示" }));
    // 検証（開く）
    expect(part).not.toHaveAttribute("data-clamped");
    expect(screen.getByRole("region", { name: "スレッドのタイトルの全文" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "タイトルを折りたたむ" })).toHaveAttribute("aria-expanded", "true");
    // 実行（折りたたむ）
    await userEvent.click(screen.getByRole("button", { name: "タイトルを折りたたむ" }));
    // 検証（折りたたむ）
    expect(part).toHaveAttribute("data-clamped");
    expect(screen.queryByRole("region")).toBeNull();
  });
});
