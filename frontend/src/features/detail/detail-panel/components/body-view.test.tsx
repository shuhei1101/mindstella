import { screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

const record = () => stubRecords({ decisions: [{ id: "D-1", title: "D-1の題", status: "未決定", body: "docs/D-1.md" }], bodies: { "docs/D-1.md": "<h2>決め方</h2>" } });

describe("BodyView", () => {
  // 見出しへ送る（正常系）
  test("body_view_when_heading", async () => {
    // 準備
    record();
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    Element.prototype.getClientRects = () => [{}] as unknown as DOMRectList;
    // 実行
    renderRoute("/spa/?tab=decisions&id=D-1&h=%E6%B1%BA%E3%82%81%E6%96%B9");
    // 検証
    expect(await screen.findByRole("heading", { name: /決め方/ })).toBeInTheDocument();
    await waitFor(() => expect(scroll).toHaveBeenCalled());
  });

  // 本文に無い見出し（正常系）
  test("body_view_when_heading_missing", async () => {
    // 準備
    record();
    // 実行
    renderRoute("/spa/?tab=decisions&id=D-1&h=%E7%84%A1%E3%81%84");
    // 検証
    await waitFor(() => expect(window.location.search).not.toContain("h="));
  });
});
