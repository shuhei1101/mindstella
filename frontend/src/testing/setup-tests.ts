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
