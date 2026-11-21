// 配る書き出しの元にする書き出し用のビルド。vite.config.ts と同じソースから、JS・CSS を中に持つ 1 枚の HTML をプラグインのプレビューのフォルダの export/ へ書き、中に持つライブラリのライセンスを同じフォルダの licenses.md へ書く
import { fileURLToPath } from "node:url";
import { defineConfig, mergeConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

import base from "./vite.config";

const OUT_DIR = fileURLToPath(new URL("./plugins/mindstella/skills/mindmap/preview/export", import.meta.url));

export default mergeConfig(
  base,
  defineConfig({
    plugins: [viteSingleFile()],
    build: { outDir: OUT_DIR, emptyOutDir: true, license: { fileName: "licenses.md" } },
  }),
);
