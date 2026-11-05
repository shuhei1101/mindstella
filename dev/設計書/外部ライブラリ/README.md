# 外部ライブラリ

採用済みの外部ライブラリ / 外部ツールのリファレンス

## 目次

<!-- table: data -->

| ページ | 概要 |
| --- | --- |
| [claude-code](./claude-code.yaml) | プラグインを読み込み、スキルを動かす CLI |
| [PyYAML](./PyYAML.yaml) | ワークスペースの YAML を読み書きする |
| [jsonschema](./jsonschema.yaml) | ワークスペースの YAML を JSON Schema で検証する |
| [marked](./marked.yaml) | プレビューで本文の差分の塊を Markdown の token ごとに分ける |
| [elkjs](./elkjs.yaml) | プレビューの検討事項のマップの配置を計算する |
| [mermaid](./mermaid.yaml) | プレビューで本文の図を SVG に描く |
| [storybook](./storybook.yaml) | プレビューの部品を状態ごとのストーリーで見る（開発用） |
| [playwright](./playwright.yaml) | プレビューのテストでブラウザを動かす（pytest-playwright。開発用） |
| [typescript](./typescript.yaml) | プレビューのスクリプトを型検査し、.ts から .js へ変換する（開発用） |
| [git](./git.yaml) | 移し替える前の写しを、git のコミットで取る・戻す |
| [mcp](./mcp.yaml) | MCP のサーバーを立て、スキルが呼ぶツールを載せる（Python の公式の SDK） |
| [tmux](./tmux.yaml) | 起動スクリプトが、MCP サーバーを渡した Claude Code を動かすセッションを立てる |
| [uvicorn](./uvicorn.yaml) | 常駐サーバーの HTTP の待ち受けを動かす |
| [starlette](./starlette.yaml) | 常駐サーバーの状態の入口の JSON を返す |
| [jsdiff](./jsdiff.yaml) | プレビューで本文と図の記法の前後を行ごとに比べる |
| [axe-core](./axe-core.yaml) | プレビューのテストでアクセシビリティの規則（WCAG）を画面に当てる（開発用） |
| [ruff](./ruff.yaml) | Python のソースを ruff.toml の規則で検査する（開発用） |
| [mdmark](./mdmark.yaml) | プレビューで本文とスレッドの書き込みの Markdown を共通のスタイルで HTML に描き、無害化する |
| [react](./react.yaml) | プレビュー（React）の画面を部品で描く |
| [vite](./vite.yaml) | プレビュー（React）を開発し、spa/ へビルドする（開発用） |
| [tailwindcss](./tailwindcss.yaml) | プレビュー（React）のスタイルをトークンのクラスで書く |
| [base-ui](./base-ui.yaml) | プレビュー（React）の shadcn/ui の部品の土台 |
| [tanstack-router](./tanstack-router.yaml) | プレビュー（React）のルートと search params の検証 |
| [tanstack-query](./tanstack-query.yaml) | プレビュー（React）がサーバーの記録を取得し、書き換えで読み直す |
| [tanstack-table](./tanstack-table.yaml) | プレビュー（React）の表の並べ替え・絞り込み・列の表示・ピン留めの状態を持つ |
| [zustand](./zustand.yaml) | プレビュー（React）の接続の状態とライト / ダークを持つ |
| [zod](./zod.yaml) | プレビュー（React）の search params を検証する |
| [orval](./orval.yaml) | OpenAPI から API の呼び出し・query・Zod・MSW を生成する（開発用） |
| [msw](./msw.yaml) | 単体テストとストーリーで API の応答を差し替える（開発用） |
| [eslint](./eslint.yaml) | プレビュー（React）のソースを規則で検査する（開発用） |
| [lefthook](./lefthook.yaml) | commit の前に lint と型検査を流す（開発用） |
| [vitest](./vitest.yaml) | プレビュー（React）の単体テストを流す（開発用） |

<!-- /table -->
