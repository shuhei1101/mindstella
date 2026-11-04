import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  framework: "@storybook/react-vite",
  stories: ["../frontend/src/**/*.stories.tsx"],
  core: { disableTelemetry: true },
  staticDirs: ["./public"],
  viteFinal: (viteConfig) => ({ ...viteConfig, root: undefined }),
};

export default config;
