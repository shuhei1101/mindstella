// 子のルートを描く外枠。描画中のエラーは errorComponent（ルーターの ErrorBoundary）で受ける
import type { QueryClient } from "@tanstack/react-query";
import { type ErrorComponentProps, Outlet, createRootRouteWithContext } from "@tanstack/react-router";

/** 描画中のエラー。画面を白くせず、エラーの文言を出す */
const RootError = ({ error }: ErrorComponentProps) => (
  <main className="p-8">
    <p role="alert">画面を描けませんでした: {error instanceof Error ? error.message : String(error)}</p>
  </main>
);

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: Outlet,
  errorComponent: RootError,
});
