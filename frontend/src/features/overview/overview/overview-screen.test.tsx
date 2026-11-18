import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, test } from "vitest";

import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

describe("OverviewScreen", () => {
  // 記録でタイルを描く（正常系）
  test("overview_screen", async () => {
    // 実行
    renderRoute("/spa/");
    // 検証
    expect(await screen.findByRole("heading", { level: 1, name: "要件出しのスキル mindmap を設計する" })).toBeInTheDocument();
    expect(document.querySelector("#tile-unread")).toBeInTheDocument();
    expect(document.querySelector("#tile-open")).toBeInTheDocument();
    expect(document.querySelector("#tile-review")).toBeInTheDocument();
    expect(document.querySelector("#tile-docs")).toBeInTheDocument();
  });

  // 422 で detail を出す（異常系）
  test("overview_screen_when_records_invalid", async () => {
    // 準備
    server.use(
      http.get("/api/records", () =>
        HttpResponse.json(
          { type: "about:blank", title: "Unprocessable Entity", status: 422, detail: "decisions.yaml: D-1.status: 決めた値ではありません" },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    // 実行
    renderRoute("/spa/");
    // 検証
    expect(await screen.findByText("decisions.yaml: D-1.status: 決めた値ではありません")).toBeInTheDocument();
    expect(document.querySelector("#tile-open")).not.toBeInTheDocument();
  });

  // すべて表示は SPA の一覧へ（正常系）
  test("overview_screen_when_show_all", async () => {
    // 準備
    renderRoute("/spa/");
    const review = await screen.findByRole("region", { name: "要見直し" });
    // 実行
    await userEvent.click(within(review).getByRole("button", { name: /すべて表示/ }));
    // 検証
    await waitFor(() => expect(decodeURIComponent(window.location.search)).toContain("f.status=要見直し"));
    expect(window.location.search).toContain("tab=decisions");
    expect(window.location.search).toContain("view=table");
  });

  // ネットワークは今の画面へ（正常系）
  test("overview_screen_when_network", async () => {
    // 準備
    renderRoute("/spa/");
    // 実行
    await userEvent.click(await screen.findByRole("link", { name: /ネットワーク/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?tab=graph"));
    expect(window.location.pathname).toBe("/spa/");
  });

  // 未読の行はスレッドへ（正常系）
  test("overview_screen_when_unread", async () => {
    // 準備
    server.use(
      http.get("/api/threads", () =>
        HttpResponse.json({
          threads: [
            {
              id: "TH-1",
              status: "open",
              tags: [],
              summary: "回答が要る検討事項 1 件",
              target: null,
              target_title: null,
              loc: null,
              posts: [{ id: "P-1", author: "ai", body: "知らせ", created: "2026-11-04T02:21:00+00:00", seen: false }],
              events: [],
            },
          ],
        }),
      ),
    );
    renderRoute("/spa/");
    const unread = await screen.findByRole("region", { name: "未読の AI の書き込み" });
    // 実行
    await userEvent.click(await within(unread).findByRole("button", { name: /TH-1/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toContain("panel=comments"));
    expect(window.location.search).toContain("thread=TH-1");
  });
});
