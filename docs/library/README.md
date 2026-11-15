# library

採用済みの外部ライブラリ / 外部ツールのリファレンス

## 目次

<!-- table: data -->

| ページ | 概要 |
| --- | --- |
| [claude-code](./LIB-489-4.yaml) | プラグインを読み込み、スキルを動かす CLI |
| [PyYAML](./LIB-489-1.yaml) | ワークスペースの YAML を読み書きする |
| [jsonschema](./LIB-489-9.yaml) | ワークスペースの YAML を JSON Schema で検証する |
| [marked](./LIB-489-11.yaml) | プレビューで本文の差分の塊を Markdown の token ごとに分ける |
| [elkjs](./LIB-489-5.yaml) | プレビューの検討事項のマップの配置を計算する |
| [mermaid](./LIB-489-14.yaml) | プレビューで本文の図を SVG に描く |
| [storybook](./LIB-489-21.yaml) | プレビューの部品を状態ごとのストーリーで見る（開発用） |
| [playwright](./LIB-489-17.yaml) | プレビューのテストでブラウザを動かす（pytest-playwright。開発用） |
| [typescript](./LIB-489-27.yaml) | プレビューのスクリプトを型検査し、.ts から .js へ変換する（開発用） |
| [git](./LIB-489-7.yaml) | 移し替える前の写しを、git のコミットで取る・戻す |
| [mcp](./LIB-489-12.yaml) | MCP のサーバーを立て、スキルが呼ぶツールを載せる（Python の公式の SDK） |
| [tmux](./LIB-489-26.yaml) | 起動スクリプトが、MCP サーバーを渡した Claude Code を動かすセッションを立てる |
| [uvicorn](./LIB-489-28.yaml) | 常駐サーバーの HTTP の待ち受けを動かす |
| [starlette](./LIB-489-20.yaml) | 常駐サーバーの状態の入口の JSON を返す |
| [jsdiff](./LIB-489-8.yaml) | プレビューで本文と図の記法の前後を行ごとに比べる |
| [axe-core](./LIB-489-2.yaml) | プレビューのテストでアクセシビリティの規則（WCAG）を画面に当てる（開発用） |
| [ruff](./LIB-489-19.yaml) | Python のソースを ruff.toml の規則で検査する（開発用） |
| [mdmark](./LIB-489-13.yaml) | プレビューで本文とスレッドの書き込みの Markdown を共通のスタイルで HTML に描き、無害化する |
| [react](./LIB-489-18.yaml) | プレビュー（React）の画面を部品で描く |
| [vite](./LIB-489-29.yaml) | プレビュー（React）を開発し、spa/ へビルドする（開発用） |
| [tailwindcss](./LIB-489-22.yaml) | プレビュー（React）のスタイルをトークンのクラスで書く |
| [@base-ui/react](./LIB-489-3.yaml) | プレビュー（React）の shadcn/ui の部品の土台 |
| [@tanstack/react-router](./LIB-489-24.yaml) | プレビュー（React）のルートと search params の検証 |
| [@tanstack/react-query](./LIB-489-23.yaml) | プレビュー（React）がサーバーの記録を取得し、書き換えで読み直す |
| [@tanstack/react-table](./LIB-489-25.yaml) | プレビュー（React）の表の並べ替え・絞り込み・列の表示・ピン留めの状態を持つ |
| [zustand](./LIB-489-32.yaml) | プレビュー（React）の接続の状態とライト / ダークを持つ |
| [zod](./LIB-489-31.yaml) | プレビュー（React）の search params を検証する |
| [orval](./LIB-489-16.yaml) | OpenAPI から API の呼び出し・query・Zod・MSW を生成する（開発用） |
| [msw](./LIB-489-15.yaml) | 単体テストとストーリーで API の応答を差し替える（開発用） |
| [eslint](./LIB-489-6.yaml) | プレビュー（React）のソースを規則で検査する（開発用） |
| [lefthook](./LIB-489-10.yaml) | commit の前に、ビルドの出力がソースと合うかを確認する（開発用） |
| [vitest](./LIB-489-30.yaml) | プレビュー（React）の単体テストを流す（開発用） |
| [claude-balancer](./LIB-531-1.yaml) | MindStella のセッションを起動するときに、一番空いている Claude Code のアカウントを借りる |
| [systemd](./LIB-531-2.yaml) | 常駐サーバーを systemd --user のユニットとして起動・停止する |

<!-- /table -->
