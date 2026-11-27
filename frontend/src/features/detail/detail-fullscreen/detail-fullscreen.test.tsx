import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, test } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

describe("DetailFullscreen", () => {
  // モーダルで開く（正常系）
  test("detail_fullscreen", async () => {
    // 実行
    renderRoute("/?tab=decisions&id=D-1&full=1");
    // 検証
    expect(await screen.findByRole("dialog", { name: /D-1の題/ })).toBeInTheDocument();
  });
  // 窓の 9/10 の大きさで開く（正常系）
  test("detail_fullscreen_size", async () => {
    // 実行
    renderRoute("/?tab=decisions&id=D-1&full=1");
    const dialog = await screen.findByRole("dialog", { name: /D-1の題/ });
    // 検証
    expect(dialog).toHaveClass("size-9/10");
    expect(dialog).not.toHaveClass("max-w-5xl");
  });
  // 下端にコメント（正常系）
  test("detail_fullscreen_when_comments", async () => {
    // 実行
    renderRoute("/?tab=decisions&id=D-1&full=1");
    const dialog = await screen.findByRole("dialog", { name: /D-1の題/ });
    // 検証
    expect(await within(dialog).findByRole("textbox", { name: /D-1 へのコメント/ })).toBeInTheDocument();
  });

  // 全画面でも案を選んで溜める（正常系）
  test("detail_fullscreen_when_choose_option", async () => {
    // 準備
    const user = userEvent.setup();
    const bodies: unknown[] = [];
    let items: unknown[] = [];
    server.use(
      http.get("*/api/comments", () => HttpResponse.json({ items, drafts: [] })),
      http.post("*/api/comments", async ({ request }) => {
        const body = (await request.json()) as { target: string; choice: { key: string } };
        bodies.push(body);
        items = [{ id: "C-1", target: body.target, loc: null, thread: null, body: null, choice: body.choice, created: "2026-11-04T02:21:00+00:00" }];
        return HttpResponse.json({ id: "C-1", created: "2026-11-04T02:21:00+00:00", count: 1 }, { status: 201 });
      }),
    );
    stubRecords({ decisions: [{ id: "D-1", title: "D-1の題", status: "未決定", options: [{ key: "A", content: "案 A" }, { key: "B", content: "案 B" }] }] });
    renderRoute("/?tab=decisions&id=D-1&full=1");
    const dialog = await screen.findByRole("dialog", { name: /D-1の題/ });
    // 実行
    await user.click(await within(dialog).findByRole("button", { name: "案 B を選ぶ" }));
    await user.click(within(dialog).getByRole("button", { name: "この案を選ぶ" }));
    // 検証
    await waitFor(() => expect(bodies).toEqual([{ target: "D-1", choice: { key: "B" } }]));
    const badge = await within(dialog).findByText("選択済み");
    expect(badge.closest("span")).toHaveClass("border-dashed");
  });
});
