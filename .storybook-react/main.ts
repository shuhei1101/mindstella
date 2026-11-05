// React のプレビューの部品のストーリー（@storybook/react-vite）。今の画面の .storybook/ とは別に動かす
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import type { StorybookConfig } from "@storybook/react-vite";

// SPA の HTML（文字の読み込みを 1 か所に保つため、ここから取り出す）
const INDEX_HTML = fileURLToPath(new URL("../frontend/index.html", import.meta.url));

// SPA の HTML の、Google Fonts への preconnect と文字の CSS の link 要素
const FONT_TAGS = /<link rel="(?:preconnect|stylesheet)" href="https:\/\/fonts\.[^>]*>/g;

/** SPA の HTML から、文字を読む link 要素を取り出す */
const fontTags = (): string => (readFileSync(INDEX_HTML, "utf8").match(FONT_TAGS) ?? []).join("\n");

const config: StorybookConfig = {
  framework: "@storybook/react-vite",
  stories: ["../frontend/src/**/*.stories.tsx"],
  core: { disableTelemetry: true },
  staticDirs: ["./public"],
  // ストーリーの画面も SPA と同じ文字で描く
  previewHead: (head) => `${head}\n${fontTags()}`,
  // vite.config.ts の root（frontend/）と出力の設定はストーリーのビルドに使わない
  viteFinal: (viteConfig) => ({ ...viteConfig, root: undefined, build: { ...viteConfig.build, outDir: undefined } }),
};

export default config;
