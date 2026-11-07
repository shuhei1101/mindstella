import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, test } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

const items = [
  { id: "C-1", target: "D-1", target_title: "D-1の題", loc: null, thread: null, body: "一つ目", created: "2026-11-01T00:00:00+00:00" },
  { id: "C-2", target: "D-1", target_title: "D-1の題", loc: null, thread: null, body: "二つ目", created: "2026-11-01T00:01:00+00:00" },
];

describe("ReviewView", () => {
  // まとめて送る（正常系）
  test("review_view", async () => {
    // 準備
    const bodies: unknown[] = [];
    server.use(
      http.get("/api/comments", () => HttpResponse.json({ items, drafts: [] })),
      http.post("/api/comments/send", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ sent: "2026-11-01T00:02:00+00:00", items: [], entered: true }, { status: 201 });
      }),
    );
    renderRoute("/spa/?panel=comments&review=1");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /まとめて送る（2 件）/ }));
    // 検証
    await waitFor(() => expect(bodies).toEqual([{ ids: ["C-1", "C-2"] }]));
  });

  // 箇所が合わない（異常系）
  test("review_view_when_stale", async () => {
    // 準備
    stubRecords({ docs: [{ id: "A-1", title: "A-1の題", status: "下書き", body: "docs/A-1.md" }], bodies: { "docs/A-1.md": "一行" } });
    server.use(
      http.get("/api/comments", () => HttpResponse.json({ items: [{ ...items[0], target: "A-1", loc: { kind: "body", start: 3, end: 3, key: null, text: "三行目" } }], drafts: [] })),
      http.post("/api/comments/send", () =>
        HttpResponse.json(
          { type: "about:blank", title: "Conflict", status: 409, detail: "箇所が合いません", stale: [{ id: "C-1", reason: "本文の 3 行目がありません" }] },
          { status: 409, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    renderRoute("/spa/?panel=comments&review=1");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /まとめて送る/ }));
    // 検証
    expect(await screen.findByRole("alert")).toHaveTextContent("本文の 3 行目がありません");
    expect(screen.getByRole("button", { name: "箇所を外す" })).toBeInTheDocument();
  });
});
