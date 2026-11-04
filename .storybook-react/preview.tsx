import type { Preview } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupWorker } from "msw/browser";

import { getGetRecordsMockHandler } from "@/shared/api/generated/preview.msw";
import "@/shared/styles/index.css";

const worker = setupWorker(
  getGetRecordsMockHandler({ settings: { summary: "MSW の話し合い" }, decisions: [{ id: "D-1", title: "問い" }], tasks: [], built_at: "2026-11-04" }),
);

const preview: Preview = {
  loaders: [async () => { await worker.start({ onUnhandledRequest: "error", quiet: true }); return {}; }],
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient()}>
        <Story />
      </QueryClientProvider>
    ),
  ],
};

export default preview;
