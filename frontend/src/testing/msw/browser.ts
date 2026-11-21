// Storybook の MSW の worker。ストーリーは `beforeEach` で `worker.use` を呼んで応答を差し替え、戻り値で元に戻す
import { setupWorker } from "msw/browser";

import { handlers } from "@/testing/msw/handlers";

export const worker = setupWorker(...handlers);
