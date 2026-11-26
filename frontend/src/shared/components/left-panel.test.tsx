import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { LeftPanel } from "@/shared/components/left-panel";
import { usePanelWidthStore } from "@/shared/stores/panel-width-store";

/** 表示の幅を差し替え、901px 以上かの matchMedia もその幅で返す */
const stubViewport = (width: number): void => {
  window.innerWidth = width;
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("min-width: 901px") ? width >= 901 : false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
};

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
  usePanelWidthStore.setState({ leftWidth: null, detailWidth: null, leftOpen: false, detailOpen: false });
});

const renderPanel = (resizerLabel?: string) =>
  render(
    <LeftPanel aria-label="コメント" resizerLabel={resizerLabel}>
      <p>中身</p>
    </LeftPanel>,
  );

describe("LeftPanel", () => {
  // 右端の区切りで幅を変えて残す（正常系）
  test("left_panel_when_resized", () => {
    // 準備
    stubViewport(1440);
    renderPanel("コメントの一覧の幅");
    const separator = screen.getByRole("separator", { name: "コメントの一覧の幅" });
    // 実行
    fireEvent.keyDown(separator, { key: "ArrowRight" });
    fireEvent.keyDown(separator, { key: "ArrowRight" });
    // 検証
    expect(screen.getByRole("complementary", { name: "コメント" }).style.width).toBe("416px");
    expect(sessionStorage.getItem("mindmap-left-panel-width")).toBe("416");
  });

  // 残した幅で開く（正常系）
  test("left_panel_when_width_saved", () => {
    // 準備
    stubViewport(1440);
    sessionStorage.setItem("mindmap-left-panel-width", "520");
    // 実行
    renderPanel("コメントの一覧の幅");
    // 検証
    expect(screen.getByRole("complementary", { name: "コメント" }).style.width).toBe("520px");
    expect(screen.getByRole("separator", { name: "コメントの一覧の幅" })).toHaveAttribute("aria-valuenow", "520");
  });

  // 詳細パネルを開いていれば上限から詳細パネルの幅を引く（正常系）
  test("left_panel_when_detail_open", () => {
    // 準備
    stubViewport(1440);
    sessionStorage.setItem("mindmap-left-panel-width", "900");
    usePanelWidthStore.setState({ leftWidth: 900, detailWidth: 640, detailOpen: true });
    // 実行
    renderPanel("コメントの一覧の幅");
    // 検証
    expect(screen.getByRole("complementary", { name: "コメント" }).style.width).toBe("400px");
    expect(screen.getByRole("separator", { name: "コメントの一覧の幅" })).toHaveAttribute("aria-valuemax", "400");
    expect(sessionStorage.getItem("mindmap-left-panel-width")).toBe("900");
  });

  // 900px 以下は区切りを描かない（正常系）
  test("left_panel_when_narrow", () => {
    // 準備
    stubViewport(900);
    // 実行
    renderPanel("コメントの一覧の幅");
    // 検証
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "コメント" }).style.width).toBe("");
  });

  // resizerLabel を省くと区切りを描かず、共有した幅で開く（正常系）
  test("left_panel_without_resizer", () => {
    // 準備
    stubViewport(1440);
    usePanelWidthStore.setState({ leftWidth: 520 });
    // 実行
    renderPanel();
    // 検証
    expect(screen.getByRole("complementary", { name: "コメント" }).style.width).toBe("520px");
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
  });

  // 描いている間だけ開いている（正常系）
  test("left_panel_open_state", () => {
    // 準備
    stubViewport(1440);
    const { unmount } = renderPanel("コメントの一覧の幅");
    const openWhileRendered = usePanelWidthStore.getState().leftOpen;
    // 実行
    unmount();
    // 検証
    expect(openWhileRendered).toBe(true);
    expect(usePanelWidthStore.getState().leftOpen).toBe(false);
  });
});
