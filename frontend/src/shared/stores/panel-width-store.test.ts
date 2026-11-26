import { afterEach, describe, expect, test } from "vitest";

import { currentLeftWidth, detailPanelMax, leftPanelMax, readStoredWidth, usePanelWidthStore } from "@/shared/stores/panel-width-store";

afterEach(() => {
  sessionStorage.clear();
  history.replaceState(null, "", "/");
  usePanelWidthStore.setState({ leftWidth: null, detailWidth: null, leftOpen: false, detailOpen: false });
});

describe("readStoredWidth", () => {
  // 残した幅か既定を返却する（正常系）
  test.each([
    { name: "残した幅", stored: "520", expected: 520 },
    { name: "無い", stored: null, expected: 384 },
    { name: "数でない", stored: "abc", expected: 384 },
    { name: "正の整数でない", stored: "0", expected: 384 },
  ])("read_stored_width: $name", ({ stored, expected }) => {
    // 準備
    history.replaceState(null, "", "/w/mindstella-x-1/");
    if (stored !== null) sessionStorage.setItem("mindmap-left-panel-width:mindstella-x-1", stored);
    // 実行・検証
    expect(readStoredWidth("mindmap-left-panel-width", 384)).toBe(expected);
  });
});

describe("leftPanelMax", () => {
  // 左のパネルの上限（正常系）
  test.each([
    { name: "詳細パネルを開いていない", viewport: 1440, detailWidth: 640, detailOpen: false, expected: 1040 },
    { name: "詳細パネルを開いている", viewport: 1440, detailWidth: 640, detailOpen: true, expected: 400 },
    { name: "詳細パネルは本文に重なる", viewport: 1000, detailWidth: 640, detailOpen: true, expected: 600 },
    { name: "下限を下回る", viewport: 1100, detailWidth: 640, detailOpen: true, expected: 320 },
  ])("left_panel_max: $name", ({ viewport, detailWidth, detailOpen, expected }) => {
    // 実行・検証
    expect(leftPanelMax(viewport, detailWidth, detailOpen)).toBe(expected);
  });
});

describe("detailPanelMax", () => {
  // 詳細パネルの上限（正常系）
  test.each([
    { name: "左のパネルを開いていない", viewport: 1440, leftWidth: 384, leftOpen: false, expected: 1040 },
    { name: "左のパネルを開いている", viewport: 1440, leftWidth: 384, leftOpen: true, expected: 656 },
    { name: "本文に重なる幅", viewport: 1000, leftWidth: 384, leftOpen: true, expected: 840 },
    { name: "下限を下回る", viewport: 1100, leftWidth: 384, leftOpen: true, expected: 480 },
  ])("detail_panel_max: $name", ({ viewport, leftWidth, leftOpen, expected }) => {
    // 実行・検証
    expect(detailPanelMax(viewport, leftWidth, leftOpen)).toBe(expected);
  });
});

describe("usePanelWidthStore", () => {
  // 確定したときだけ保存領域に記載する（正常系）
  test("commit_left_width", () => {
    // 準備
    const { setLeftWidth, commitLeftWidth } = usePanelWidthStore.getState();
    // 実行
    setLeftWidth(500);
    const beforeCommit = sessionStorage.getItem("mindmap-left-panel-width");
    commitLeftWidth(520);
    // 検証
    expect(beforeCommit).toBeNull();
    expect(sessionStorage.getItem("mindmap-left-panel-width")).toBe("520");
    expect(usePanelWidthStore.getState().leftWidth).toBe(520);
  });
});

describe("currentLeftWidth", () => {
  // 適用した幅か、まだなら保存領域の幅を返却する（正常系）
  test.each([
    { name: "まだ適用していない", leftWidth: null, expected: 520 },
    { name: "適用した", leftWidth: 500, expected: 500 },
  ])("current_left_width: $name", ({ leftWidth, expected }) => {
    // 準備
    sessionStorage.setItem("mindmap-left-panel-width", "520");
    usePanelWidthStore.setState({ leftWidth });
    // 実行・検証
    expect(currentLeftWidth(usePanelWidthStore.getState())).toBe(expected);
  });
});
