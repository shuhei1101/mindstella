import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { queryClient, router } from "@/app/router";
import { subscribeEvents } from "@/shared/adapters/events";
import "@/shared/styles/index.css";

const container = document.querySelector("#root");
if (container !== null) {
  subscribeEvents(queryClient);
  createRoot(container).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </StrictMode>,
  );
}
