import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { getLibrary } from "@/testing/libraries";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

const record = () => stubRecords({ decisions: [{ id: "D-1", title: "D-1の題", status: "未決定", body: "docs/D-1.md" }], bodies: { "docs/D-1.md": "<h2>決め方</h2>" } });

/** 差分の表示で開く検討事項（選んだ時点の本文は「前の行」、今の本文は「今の行」） */
const diffRecord = () =>
  stubRecords({
    decisions: [{ id: "D-1", title: "D-1の題", status: "未決定", body: "docs/D-1.md", history: [{ seq: 2, at: "2026-11-02T00:00:00+00:00", before: {}, body_diff: [{ line: 1, now: ["今の行"], before: ["前の行"] }] }] }],
    bodies: { "docs/D-1.md": "今の行\n" },
    changes: { last_seq: 2, sets: [{ id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 2, added: [], changed: ["D-1"] }, { id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: [], changed: [] }], pending: { added: [], changed: [] } },
  });

/** mdmark の `mount` に渡った指定 */
type MountOptions = { markdown: string; baseMarkdown?: string; diffMode?: string; diffSource?: { revisions: (docId: string) => Promise<unknown[]> } };

/** mdmark の `mount` を見張る */
const spyMount = () => vi.spyOn(getLibrary("mdmark") as { mount: (root: HTMLElement, options: MountOptions) => unknown }, "mount");

describe("BodyView", () => {
  // 見出しへ送る（正常系）
  test("body_view_when_heading", async () => {
    // 準備
    record();
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    Element.prototype.getClientRects = () => [{}] as unknown as DOMRectList;
    // 実行
    renderRoute("/?tab=decisions&id=D-1&h=%E6%B1%BA%E3%82%81%E6%96%B9");
    // 検証
    expect(await screen.findByRole("heading", { name: /決め方/ })).toBeInTheDocument();
    await waitFor(() => expect(scroll).toHaveBeenCalled());
  });

  // 本文に無い見出し（正常系）
  test("body_view_when_heading_missing", async () => {
    // 準備
    record();
    // 実行
    renderRoute("/?tab=decisions&id=D-1&h=%E7%84%A1%E3%81%84");
    // 検証
    await waitFor(() => expect(window.location.search).not.toContain("h="));
  });

  // 描いた結果は比較元の Markdown で描く（正常系）
  test("body_view_when_diff_rendered", async () => {
    // 準備
    diffRecord();
    const mount = spyMount();
    // 実行
    renderRoute("/?tab=decisions&id=D-1&diff=V-2");
    // 検証
    await waitFor(() => expect(mount.mock.calls.some(([, options]) => options.markdown === "今の行\n" && options.baseMarkdown?.includes("前の行") === true)).toBe(true));
    mount.mockRestore();
  });

  // 原文の差分は取り出し元で描く（正常系）
  test("body_view_when_diff_source", async () => {
    // 準備
    diffRecord();
    const mount = spyMount();
    renderRoute("/?tab=decisions&id=D-1&diff=V-2");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "原文の差分" }));
    // 検証
    await waitFor(() => expect(mount.mock.calls.some(([, options]) => options.diffMode === "open")).toBe(true));
    const options = mount.mock.calls.filter(([, call]) => call.diffMode === "open").at(-1)?.[1];
    expect(await options?.diffSource?.revisions("D-1")).toHaveLength(2);
    expect(screen.queryByRole("toolbar", { name: "変わった箇所" })).not.toBeInTheDocument();
    mount.mockRestore();
  });

  // 原文の差分を押し直すと描き直す（正常系）
  test("body_view_when_diff_source_pressed_again", async () => {
    // 準備
    diffRecord();
    const mount = spyMount();
    renderRoute("/?tab=decisions&id=D-1&diff=V-2");
    const button = await screen.findByRole("button", { name: "原文の差分" });
    // 実行
    await userEvent.click(button);
    await userEvent.click(button);
    // 検証
    await waitFor(() => expect(mount.mock.calls.filter(([, options]) => options.diffMode === "open")).toHaveLength(2));
    mount.mockRestore();
  });
});
