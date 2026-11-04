import { defineConfig } from "orval";

export default defineConfig({
  preview: {
    input: "./frontend/openapi.yaml",
    output: {
      target: "./frontend/src/shared/api/generated/preview.ts",
      schemas: "./frontend/src/shared/api/generated/model",
      client: "react-query",
      mock: true,
      clean: true,
      override: {
        mutator: { path: "./frontend/src/shared/adapters/api-client.ts", name: "apiClient" },
      },
    },
  },
  previewZod: {
    input: "./frontend/openapi.yaml",
    output: {
      target: "./frontend/src/shared/api/generated/preview.zod.ts",
      client: "zod",
    },
  },
});
