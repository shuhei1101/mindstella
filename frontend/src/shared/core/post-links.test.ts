import { describe, expect, test, vi } from "vitest";

import { linkThreadIds } from "@/shared/core/post-links";

describe("linkThreadIds", () => {
  // 記録にあるスレッド・書き込みの ID だけをボタンにする（正常系）
  test("link_thread_ids", () => {
    // 準備
    const root = document.createElement("div");
    const source = "TH-2 と TH-2-3 と TH-2-9 と TH-99";
    root.innerHTML = `<p>${source}</p>`;
    const onOpen = vi.fn();
    const threads = (id: string) => (id === "TH-2" ? { title: "トップバーの見直し", posts: ["TH-2-1", "TH-2-2", "TH-2-3"] } : null);
    // 実行
    linkThreadIds({ root, threads, onOpen });
    for (const button of root.querySelectorAll<HTMLButtonElement>("button")) button.click();
    // 検証
    expect([...root.querySelectorAll("button")].map((button) => button.textContent)).toEqual(["TH-2", "TH-2-3"]);
    expect(root.textContent).toBe(source);
    expect(onOpen.mock.calls).toEqual([
      ["TH-2", null],
      ["TH-2", "TH-2-3"],
    ]);
  });
});
