// PoC: React の画面を JS・CSS を中に持つ 1 枚の HTML にする書き出し用のビルド
import { fileURLToPath } from "node:url";
import { defineConfig, mergeConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

import base from "../vite.config";

const OUT_DIR = fileURLToPath(new URL("./dist-export", import.meta.url));

export default mergeConfig(
  base,
  defineConfig({
    plugins: [viteSingleFile()],
    build: { outDir: OUT_DIR, emptyOutDir: true },
  }),
);
