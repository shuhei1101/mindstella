// Provider とルーターつきで画面を描く
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { render } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "@/app/query-client";
import { createAppRouter } from "@/app/router";
import { FakeEventSource } from "@/testing/fake-event-source";

/** URL のパスでルートを開き、その画面を描く */
export const renderRoute = (path: string) => {
  vi.stubGlobal("EventSource", FakeEventSource);
  window.history.replaceState(null, "", path);
  const queryClient = createQueryClient();
  const router = createAppRouter(queryClient);
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
};
