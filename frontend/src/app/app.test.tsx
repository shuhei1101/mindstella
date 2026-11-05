import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { App } from "@/app/app";
import { createQueryClient } from "@/app/query-client";
import { createAppRouter } from "@/app/router";
import { FakeEventSource } from "@/testing/fake-event-source";

describe("App", () => {
  // ルートの画面を描く（正常系）
  test("app", async () => {
    // 準備
    vi.stubGlobal("EventSource", FakeEventSource);
    window.history.replaceState(null, "", "/spa/");
    const queryClient = createQueryClient();
    const router = createAppRouter(queryClient);
    // 実行
    render(<App queryClient={queryClient} router={router} />);
    // 検証
    expect(await screen.findByRole("heading", { level: 1, name: "要件出しのスキル mindmap を設計する" })).toBeInTheDocument();
    expect(FakeEventSource.last?.url).toBe("/api/events");
  });
});
