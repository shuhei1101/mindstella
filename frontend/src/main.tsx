// 起動: QueryClient とルーターを作り、#root に描く
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/app";
import { createQueryClient } from "@/app/query-client";
import { createAppRouter } from "@/app/router";
import "@/shared/styles/index.css";

const container = document.querySelector("#root");
if (container !== null) {
  const queryClient = createQueryClient();
  const router = createAppRouter(queryClient);
  createRoot(container).render(
    <StrictMode>
      <App queryClient={queryClient} router={router} />
    </StrictMode>,
  );
}
