import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { App } from "@/app/app";
import { createQueryClient } from "@/app/query-client";
import { createAppRouter } from "@/app/router";
import { resetEmbeddedDataForTest } from "@/shared/core/embedded";
import { FakeEventSource } from "@/testing/fake-event-source";
import { RECORDS } from "@/testing/msw/handlers";

describe("App", () => {
  afterEach(() => {
    document.body.replaceChildren();
    resetEmbeddedDataForTest();
    FakeEventSource.last = undefined;
  });

  // ルートの画面を描く（正常系）
  test("app", async () => {
    // 準備
    vi.stubGlobal("EventSource", FakeEventSource);
    window.history.replaceState(null, "", "/");
    const queryClient = createQueryClient();
    const router = createAppRouter(queryClient);
    // 実行
    render(<App queryClient={queryClient} router={router} />);
    // 検証
    expect(await screen.findByRole("heading", { level: 1, name: "要件出しのスキル mindmap を設計する" })).toBeInTheDocument();
    expect(FakeEventSource.last?.url).toBe("/api/events");
  });

  // 配る書き出しは書き換えの通知へつながない（正常系）
  test("app_when_embedded", async () => {
    // 準備
    vi.stubGlobal("EventSource", FakeEventSource);
    const data = document.createElement("script");
    data.type = "application/json";
    data.id = "mindmap-data";
    data.textContent = JSON.stringify(RECORDS);
    document.body.append(data);
    window.history.replaceState(null, "", "/x/export.html#/");
    const queryClient = createQueryClient();
    const router = createAppRouter(queryClient);
    // 実行
    render(<App queryClient={queryClient} router={router} />);
    // 検証
    expect(await screen.findByRole("heading", { level: 1, name: "要件出しのスキル mindmap を設計する" })).toBeInTheDocument();
    expect(FakeEventSource.last).toBeUndefined();
  });
});
