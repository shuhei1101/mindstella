// Vitest の MSW のサーバー
import { setupServer } from "msw/node";

import { handlers } from "@/testing/msw/handlers";

export const server = setupServer(...handlers);
