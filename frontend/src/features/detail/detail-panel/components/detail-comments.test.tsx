import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

const doc = { id: "A-1", title: "A-1の題", status: "下書き", body: "docs/A-1.md" };

afterEach(() => {
  localStorage.clear();
});

describe("DetailComments", () => {
  // 箇所を添えて溜める（正常系）
  test("detail_comments", async () => {
    // 準備
    // テストの mdmark は本文をそのまま入れるため、mdmark が付ける行の印を本文に書いておく
    stubRecords({ docs: [doc], bodies: { "docs/A-1.md": '<p data-line-start="1">一行目</p><p data-line-start="3">二行目</p><p data-line-start="5">三行目</p>' } });
    server.use(http.get("/api/comments", () => HttpResponse.json({ items: [], drafts: [] })));
    const bodies: unknown[] = [];
    server.use(
      http.post("/api/comments", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ id: "C-1", created: "2026-11-01T00:00:00+00:00", count: 1 }, { status: 201 });
      }),
    );
    renderRoute("/spa/?tab=docs&id=A-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    const line = await within(panel).findByText("二行目");
    // 実行
    const range = document.createRange();
    range.selectNodeContents(line);
    window.getSelection()?.removeAllRanges();
    window.getSelection()?.addRange(range);
    line.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    await userEvent.click(await screen.findByRole("button", { name: "選んだ箇所にコメント" }));
    await userEvent.type(within(panel).getByRole("textbox", { name: /A-1 へのコメント/ }), "ここを直す");
    await userEvent.click(within(panel).getByRole("button", { name: /レビューに追加/ }));
    // 検証
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ target: "A-1", loc: { kind: "body", start: 3, end: 3 }, body: "ここを直す" });
  });

  // 並びを切り替える（正常系）
  test("detail_comments_when_order", async () => {
    // 準備
    stubRecords({ docs: [doc], bodies: { "docs/A-1.md": "本文" } });
    server.use(
      http.get("/api/comments", () =>
        HttpResponse.json({
          items: [
            { id: "C-1", target: "A-1", target_title: "A-1の題", loc: null, thread: null, body: "古い", created: "2026-11-01T00:00:00+00:00" },
            { id: "C-2", target: "A-1", target_title: "A-1の題", loc: null, thread: null, body: "新しい", created: "2026-11-01T00:01:00+00:00" },
          ],
          drafts: [],
        }),
      ),
    );
    renderRoute("/spa/?tab=docs&id=A-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    // 実行
    await userEvent.click(await within(panel).findByRole("button", { name: "コメントの並び: 新しい順" }));
    // 検証
    const bodiesInOrder = within(panel).getAllByText(/^(古い|新しい)$/).map((element) => element.textContent);
    expect(bodiesInOrder).toEqual(["古い", "新しい"]);
    expect((JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}") as Record<string, unknown>)["reviewOrder"]).toBe("oldest");
  });

  // 開閉を覚え、入口で開く（正常系）
  test("detail_comments_when_toggle_open", async () => {
    // 準備
    const other = { id: "A-2", title: "A-2の題", status: "下書き", body: "docs/A-2.md" };
    stubRecords({
      docs: [doc, other],
      bodies: { "docs/A-1.md": '<p data-line-start="1">一行目</p><p data-line-start="3">二行目</p>', "docs/A-2.md": "本文" },
    });
    server.use(http.get("/api/comments", () => HttpResponse.json({ items: [], drafts: [] })));
    renderRoute("/spa/?tab=docs&id=A-1");
    // 履歴を進めて別の項目を開く（ルーターは popstate で URL を読み直す）
    const open = (id: string): void => {
      window.history.pushState(null, "", `/spa/?tab=docs&id=${id}`);
      window.dispatchEvent(new PopStateEvent("popstate"));
    };
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    // 実行（閉じてから別の項目へ移る）
    await userEvent.click(await within(panel).findByRole("button", { name: "コメントの入力を閉じる" }));
    open("A-2");
    // 検証
    const stored = (): unknown => (JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}") as Record<string, unknown>)["commentFormClosed"];
    expect(stored()).toBe(true);
    await within(panel).findByText(/A-2/);
    expect(within(panel).queryByRole("textbox", { name: /A-2 へのコメント/ })).toBeNull();
    expect(within(panel).getByRole("button", { name: "コメントの入力を開く" })).toBeInTheDocument();
    // 実行（閉じたまま A-1 の本文を選んで入口を押す）
    open("A-1");
    const line = await within(panel).findByText("二行目");
    const range = document.createRange();
    range.selectNodeContents(line);
    window.getSelection()?.removeAllRanges();
    window.getSelection()?.addRange(range);
    line.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    await userEvent.click(await screen.findByRole("button", { name: "選んだ箇所にコメント" }));
    // 検証
    await waitFor(() => expect(stored() ?? null).toBeNull());
    expect(within(panel).getByRole("textbox", { name: /A-1 へのコメント/ })).toHaveFocus();
  });
});
