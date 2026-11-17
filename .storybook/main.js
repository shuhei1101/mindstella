// Storybook の設定。部品（plugins/mindstella/skills/mindmap/preview/components/）の状態をストーリーとして開く。

import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

// プレビューのフォルダ（雛形・CSS・tsc が生成した JavaScript を持つ）
const PREVIEW_DIR = fileURLToPath(new URL("../plugins/mindstella/skills/mindmap/preview", import.meta.url));

// staticDirs で配るときの URL の頭
const PREVIEW_URL = "/preview";

// 起動する app.js（読むと画面を描き始めるので、ストーリーの画面には読まない）
const APP_SCRIPT = "app.js";

// 雛形の文字の link 要素と描画のライブラリの script 要素（版と integrity を雛形の 1 か所に保つため、雛形から取り出す。雛形は mdmark の差し込み口の印だけを持つ）
const TEMPLATE_TAGS = /<link rel="stylesheet" href="https:\/\/fonts[^>]*>|<script src="https:\/\/cdn[^>]*><\/script>/g;

// Storybook の画面が読む mdmark の `dist/`。設定を持たないときの既定（`latest` = `@develop`）で、サーバーの `mdmark_dist_url` と同じ組み立て
const MDMARK_STORYBOOK_URL = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark@develop/dist";

/** 雛形から文字と描画のライブラリを読むタグを取り出し、mdmark の読み込みを足して返す */
function templateTags() {
  const template = readFileSync(`${PREVIEW_DIR}/template.html`, "utf8");
  const mdmark = [
    `<link rel="stylesheet" href="${MDMARK_STORYBOOK_URL}/index.css" crossorigin="anonymous">`,
    `<script type="application/json" id="mindmap-mdmark-config">${JSON.stringify({ js: `${MDMARK_STORYBOOK_URL}/index.js`, map: {} })}</script>`,
  ];
  return [...(template.match(TEMPLATE_TAGS) ?? []), ...mdmark].join("\n");
}

/** 部品が使う tsc の生成した JavaScript の script 要素（起動する app.js を除く）。読んだだけでは何も描かない */
function componentScripts() {
  return readdirSync(PREVIEW_DIR, { recursive: true })
    .map((path) => String(path).replaceAll("\\", "/"))
    .filter((path) => path.endsWith(".js") && path !== APP_SCRIPT)
    .sort()
    .map((path) => `<script src="${PREVIEW_URL}/${path}"></script>`)
    .join("\n");
}

/** @type {import("@storybook/html-vite").StorybookConfig} */
const config = {
  framework: "@storybook/html-vite",
  stories: ["../plugins/mindstella/skills/mindmap/preview/components/*.stories.ts"],
  core: { disableTelemetry: true },
  staticDirs: [{ from: PREVIEW_DIR, to: PREVIEW_URL }],
  // ストーリーの画面の head に、デザインのトークンと部品の CSS、描画のライブラリ、部品の JavaScript を差し込む
  previewHead: (head) => `${head}
${templateTags()}
<link rel="stylesheet" href="${PREVIEW_URL}/tokens.css">
<link rel="stylesheet" href="${PREVIEW_URL}/style.css">
${componentScripts()}`,
};

export default config;
