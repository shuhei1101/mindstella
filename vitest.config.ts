// React の側の単体テスト（Vitest + Testing Library）の設定
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const SRC_DIR = fileURLToPath(new URL("./frontend/src", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": SRC_DIR } },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["frontend/src/**/*.test.{ts,tsx}"],
    setupFiles: ["./frontend/src/testing/setup-tests.ts"],
    coverage: { include: ["frontend/src/**"], exclude: ["frontend/src/routes/**", "frontend/src/shared/api/generated/**"] },
  },
});
