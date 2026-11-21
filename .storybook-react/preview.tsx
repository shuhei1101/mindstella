// ストーリーの共通の準備: トークンと Tailwind・MSW の handler・QueryClient
import type { Preview } from "@storybook/react-vite";
import { QueryClientProvider } from "@tanstack/react-query";

import { createQueryClient } from "@/app/query-client";
import { setMdmarkSettings } from "@/shared/adapters/libraries";
import { worker } from "@/testing/msw/browser";
import "@/shared/styles/index.css";

const preview: Preview = {
  loaders: [
    async () => {
      // 描画のライブラリを読む前に、Storybook の起動時に決めた mdmark の ref を渡す
      const ref = document.querySelector<HTMLMetaElement>('meta[name="mindstella-mdmark-ref"]')?.content;
      setMdmarkSettings(undefined, ref);
      await worker.start({ onUnhandledFrame: "bypass", quiet: true });
      return {};
    },
  ],
  decorators: [
    (Story) => (
      <QueryClientProvider client={createQueryClient()}>
        <Story />
      </QueryClientProvider>
    ),
  ],
};

export default preview;
