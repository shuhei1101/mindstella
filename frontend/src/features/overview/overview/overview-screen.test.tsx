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
    expect(document.querySelector("#tile-next")).toBeInTheDocument();
    expect(document.querySelector("#tile-goal")).toBeInTheDocument();
    expect(document.querySelector("#tile-review")).toBeInTheDocument();
    expect(document.querySelector("#tile-hold")).toBeInTheDocument();
    expect(document.querySelector("#tile-running")).toBeInTheDocument();
    expect(document.querySelector("#tile-progress")).toBeInTheDocument();
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
    expect(document.querySelector("#tile-next")).not.toBeInTheDocument();
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
});
