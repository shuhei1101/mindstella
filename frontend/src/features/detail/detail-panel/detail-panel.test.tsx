import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { usePanelWidthStore } from "@/shared/stores/panel-width-store";
import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

const decision = {
  id: "D-1",
  title: "D-1の題",
  status: "未決定",
  body: "docs/D-1.md",
  options: [{ key: "A", content: "案 A" }],
  history: [{ seq: 2, at: "2026-11-02T00:00:00+00:00", before: {}, body_diff: [{ line: 1, now: ["今の行"], before: ["前の行"] }] }],
};
const changes = { last_seq: 2, sets: [{ id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 2, added: [], changed: ["D-1"] }, { id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: [], changed: [] }], pending: { added: [], changed: [] } };

describe("DetailPanel", () => {
  // 項目を描く（正常系）
  test("detail_panel", async () => {
    // 準備
    stubRecords({ decisions: [decision, { id: "D-2", title: "D-2の題", status: "未決定", related: [{ to: "D-1", type: "depends_on" }] }], bodies: { "docs/D-1.md": "本文の文" } });
    // 実行
    renderRoute("/?tab=decisions&id=D-1");
    // 検証
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    expect(panel).toHaveTextContent("D-1の題");
    expect(panel).toHaveTextContent("案 A");
    expect(panel).toHaveTextContent("本文の文");
    await userEvent.click(within(panel).getByRole("tab", { name: "関連" }));
    expect(panel).toHaveTextContent("D-2の題");
  });

  // 本文の差分（正常系）
  test("detail_panel_when_diff", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "今の行\n" }, changes });
    // 実行
    renderRoute("/?tab=decisions&id=D-1&diff=V-2");
    // 検証
    expect(await screen.findByRole("group", { name: "本文の差分の見せ方" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "描いた結果" })).toHaveAttribute("aria-pressed", "true");
  });

  // 本文のスクロール位置へ戻す（正常系）
  test("detail_panel_when_body_scroll_saved", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "本文" } });
    sessionStorage.setItem("mindmap-body-scroll", '{"D-1":80}');
    // 実行
    renderRoute("/?tab=decisions&id=D-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    const body = panel.querySelector<HTMLElement>(".panel-body");
    // 検証
    await waitFor(() => expect(body?.scrollTop).toBe(80));
    sessionStorage.clear();
  });

  // ワークスペースごとのキーに残した幅で開く（正常系）
  test("detail_panel_when_width_saved", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "本文" } });
    // 880px が上限（表示の幅 − 400）に収まる表示の幅
    window.innerWidth = 1440;
    sessionStorage.setItem("mindmap-panel-width:mindstella-x-1", "880");
    sessionStorage.setItem("mindmap-panel-width", "1000");
    // 実行
    renderRoute("/w/mindstella-x-1/?tab=decisions&id=D-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    // 検証
    expect(panel.style.width).toBe("880px");
    sessionStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  // 編集の表示（正常系）
  test("detail_panel_when_editing", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "本文" } });
    renderRoute("/?tab=decisions&id=D-1");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "編集する" }));
    // 検証
    expect(await screen.findByRole("textbox", { name: "タイトル" })).toHaveValue("D-1の題");
  });

  // 下端にコメント（正常系）
  test("detail_panel_when_comments", async () => {
    // 準備
    stubRecords({ decisions: [decision], changes });
    // 実行
    renderRoute("/?tab=decisions&id=D-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    // 検証
    const input = await within(panel).findByRole("textbox", { name: /D-1 へのコメント/ });
    const scroller = within(panel).getByRole("region", { name: "詳細の本文" });
    expect(scroller).not.toContainElement(input);
    await userEvent.click(within(panel).getByRole("tab", { name: "コメント" }));
    expect(scroller).toContainElement(within(panel).getByRole("heading", { name: "レビュー中のコメント" }));
  });
  // 見出しのコメントの一覧のボタンで、その項目で絞ったコメントの一覧を開く（正常系）
  test("detail_panel_when_comments_button", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "本文" } });
    const { unmount } = renderRoute("/?id=D-1&panel=comments&thread=TH-1&tstatus=all");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    const before = window.history.length;
    // 実行
    await userEvent.click(within(panel).getByRole("button", { name: "D-1 のコメントの一覧を開く" }));
    // 検証
    await waitFor(() => expect(window.location.search).toContain("ttarget=D-1"));
    expect(window.location.search).toContain("panel=comments");
    expect(window.location.search).toContain("tstatus=all");
    expect(window.location.search).not.toContain("thread=");
    expect(window.history.length).toBe(before);
    // 全画面にはボタンが無い
    unmount();
    renderRoute("/?id=D-1&full=1");
    await waitFor(() => expect(document.body).toHaveTextContent("D-1の題"));
    expect(screen.queryByRole("button", { name: "D-1 のコメントの一覧を開く" })).toBeNull();
  });
  // タブで関連とコメントへ切り替え、項目を移ると本文に戻る（正常系）
  test("detail_panel_when_tabs", async () => {
    // 準備
    stubRecords({ decisions: [decision, { id: "D-2", title: "D-2の題", status: "未決定", related: [{ to: "D-1", type: "see_also" }] }], bodies: { "docs/D-1.md": "本文の文" } });
    renderRoute("/?tab=decisions&id=D-2");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    // 実行
    await userEvent.click(within(panel).getByRole("tab", { name: "関連" }));
    // 検証
    expect(within(panel).getByRole("heading", { name: "関連する項目" })).toBeInTheDocument();
    // 実行
    await userEvent.click(within(panel).getByRole("button", { name: /D-1/ }));
    // 検証
    await waitFor(() => expect(panel).toHaveTextContent("D-1の題"));
    expect(within(panel).getByRole("tab", { name: "本文" })).toHaveAttribute("aria-selected", "true");
  });

  // 目次から見出しへ移る（正常系）
  test("detail_panel_when_toc", async () => {
    // 準備
    stubRecords({ decisions: [{ ...decision, history: [] }], bodies: { "docs/D-1.md": "# 目的\n\n本文\n\n## 保存先\n\n本文" } });
    renderRoute("/?tab=decisions&id=D-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    await userEvent.click(within(panel).getByRole("tab", { name: "関連" }));
    const before = window.history.length;
    // 実行
    await userEvent.click(within(panel).getByRole("button", { name: "本文の目次" }));
    await userEvent.click(screen.getByRole("button", { name: "保存先" }));
    // 検証
    expect(within(panel).getByRole("tab", { name: "本文" })).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("h")).toBe("保存先"));
    expect(window.history.length).toBe(before);
  });

  // 左のパネルを開いていれば上限から左のパネルの幅を引く（正常系）
  test("detail_panel_when_left_open", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "本文" } });
    window.innerWidth = 1440;
    usePanelWidthStore.setState({ leftOpen: true, leftWidth: 384 });
    renderRoute("/?tab=decisions&id=D-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    const separator = within(panel).getByRole("separator", { name: "詳細パネルの幅" });
    // 実行
    fireEvent.keyDown(separator, { key: "End" });
    // 検証
    expect(separator).toHaveAttribute("aria-valuemax", "656");
    await waitFor(() => expect(panel.style.width).toBe("656px"));
    usePanelWidthStore.setState({ leftOpen: false, leftWidth: null, detailWidth: null });
    sessionStorage.clear();
  });

  // 窓の幅を狭めると上限と幅が追従する（正常系）
  test("detail_panel_when_viewport_resized", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "本文" } });
    window.innerWidth = 1440;
    usePanelWidthStore.setState({ leftOpen: true, leftWidth: 384, detailWidth: 640 });
    renderRoute("/?tab=decisions&id=D-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    const separator = within(panel).getByRole("separator", { name: "詳細パネルの幅" });
    expect(panel.style.width).toBe("640px");
    // 実行
    act(() => {
      window.innerWidth = 1100;
      window.dispatchEvent(new Event("resize"));
    });
    // 検証
    await waitFor(() => expect(separator).toHaveAttribute("aria-valuemax", "480"));
    expect(panel.style.width).toBe("480px");
    usePanelWidthStore.setState({ leftOpen: false, leftWidth: null, detailWidth: null });
    sessionStorage.clear();
  });
});
