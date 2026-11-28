import { act, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, test } from "vitest";

import { toSessionStatus, useSessionStatus } from "@/shared/hooks/use-session-status";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

describe("toSessionStatus", () => {
  // 応答をバーの状態にする（正常系）
  test.each([
    { name: "restarting", response: { status: "restarting", last_error: null, waiting: 2, warnings: [] }, retrying: false, closed: false, expected: { kind: "restarting", waiting: 2 } },
    { name: "failed", response: { status: "crashed", last_error: "x", waiting: 0, warnings: [] }, retrying: true, closed: false, expected: { kind: "failed", reason: "x", retrying: true } },
    { name: "crashed_without_error", response: { status: "crashed", last_error: null, waiting: 0, warnings: [] }, retrying: false, closed: false, expected: { kind: "running" } },
    { name: "launch_record_missing", response: { status: "running", last_error: null, waiting: 0, warnings: ["launch_record_missing"] }, retrying: false, closed: false, expected: { kind: "launch_record_missing" } },
    { name: "warning_closed", response: { status: "running", last_error: null, waiting: 0, warnings: ["launch_record_missing"] }, retrying: false, closed: true, expected: { kind: "running" } },
  ] as const)("to_session_status: $name", ({ response, retrying, closed, expected }) => {
    expect(toSessionStatus({ ...response, warnings: [...response.warnings] }, retrying, closed)).toEqual(expected);
  });
});

describe("useSessionStatus", () => {
  // 状態を取得し、再起動して取得し直す（正常系）
  test("use_session_status", async () => {
    // 準備
    server.use(http.get("*/api/session", () => HttpResponse.json({ status: "crashed", last_error: "x", waiting: 0, warnings: [] })));
    const { result } = await renderPreviewHook("/", useSessionStatus);
    await waitFor(() => expect(result.current?.status).toEqual({ kind: "failed", reason: "x", retrying: false }));
    server.use(
      http.post("*/api/session/restart", () => HttpResponse.json({ status: "restarting", warnings: [] }, { status: 202 })),
      http.get("*/api/session", () => HttpResponse.json({ status: "restarting", last_error: null, waiting: 0, warnings: [] })),
    );
    // 実行
    act(() => result.current?.restart());
    // 検証
    await waitFor(() => expect(result.current?.status).toEqual({ kind: "restarting", waiting: 0 }));
  });

  // 再起動の途中以外で断られた 409 は理由を出し、再起動の途中の 409 は出さない（異常系）
  test.each([
    { name: "closed", stage: "closed", expected: "クローズ済みです" },
    { name: "restarting", stage: "restarting", expected: "x" },
  ])("use_session_status_when_conflict: $name", async ({ stage, expected }) => {
    // 準備
    server.use(
      http.get("*/api/session", () => HttpResponse.json({ status: "crashed", last_error: "x", waiting: 0, warnings: [] })),
      http.post("*/api/session/restart", () =>
        HttpResponse.json({ type: "about:blank", title: "Conflict", status: 409, detail: "クローズ済みです", stage }, { status: 409, headers: { "Content-Type": "application/problem+json" } }),
      ),
    );
    const { result } = await renderPreviewHook("/", useSessionStatus);
    await waitFor(() => expect(result.current?.status).toEqual({ kind: "failed", reason: "x", retrying: false }));
    // 実行
    act(() => result.current?.restart());
    // 検証
    await waitFor(() => expect(result.current?.status).toEqual({ kind: "failed", reason: expected, retrying: false }));
  });

  // 閉じた警告を再起動まで出さない（正常系）
  test("use_session_status_when_warning_closed", async () => {
    // 準備
    server.use(http.get("*/api/session", () => HttpResponse.json({ status: "running", last_error: null, waiting: 0, warnings: ["launch_record_missing"] })));
    const { result, queryClient } = await renderPreviewHook("/", useSessionStatus);
    await waitFor(() => expect(result.current?.status).toEqual({ kind: "launch_record_missing" }));
    // 実行
    act(() => result.current?.closeWarning());
    // 検証
    expect(result.current?.status).toEqual({ kind: "running" });
    server.use(http.get("*/api/session", () => HttpResponse.json({ status: "restarting", last_error: null, waiting: 0, warnings: [] })));
    await act(() => queryClient.invalidateQueries());
    await waitFor(() => expect(result.current?.status).toEqual({ kind: "restarting", waiting: 0 }));
    server.use(http.get("*/api/session", () => HttpResponse.json({ status: "running", last_error: null, waiting: 0, warnings: ["launch_record_missing"] })));
    await act(() => queryClient.invalidateQueries());
    await waitFor(() => expect(result.current?.status).toEqual({ kind: "launch_record_missing" }));
  });
});
