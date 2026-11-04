// React のプレビューの部品のストーリー（@storybook/react-vite）。今の画面の .storybook/ とは別に動かす
import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  framework: "@storybook/react-vite",
  stories: ["../frontend/src/**/*.stories.tsx"],
  core: { disableTelemetry: true },
  staticDirs: ["./public"],
  // vite.config.ts の root（frontend/）と出力の設定はストーリーのビルドに使わない
  viteFinal: (viteConfig) => ({ ...viteConfig, root: undefined, build: { ...viteConfig.build, outDir: undefined } }),
};

export default config;
