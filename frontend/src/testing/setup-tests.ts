// 単体テストの共通の準備: jest-dom の matcher・MSW のサーバー・端末の保存領域の後始末
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "@/testing/msw/server";

// jsdom は ResizeObserver を持たないため、大きさを知らせない空の実装を置く
class NoopResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
globalThis.ResizeObserver ??= NoopResizeObserver;

// jsdom は window.scrollTo を持たないため、ルーターのスクロール位置の復元が呼ぶ空の実装を置く
window.scrollTo = () => undefined;

// jsdom は popover の API と document.fonts を持たないため、ツールチップが呼ぶ空の実装を置く
for (const name of ["showPopover", "hidePopover"] as const) {
  if (!(name in HTMLElement.prototype)) Object.defineProperty(HTMLElement.prototype, name, { value: () => undefined, configurable: true, writable: true });
}
if (!("fonts" in document)) Object.defineProperty(document, "fonts", { value: { ready: Promise.resolve() } });

beforeAll(() => {
  // handler の無い要求はテストを失敗させる
  server.listen({ onUnhandledFrame: "error" });
});

afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
});

afterAll(() => {
  server.close();
});
