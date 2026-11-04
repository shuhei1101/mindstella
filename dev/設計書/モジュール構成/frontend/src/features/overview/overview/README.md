# overview

`frontend/src/features/overview/overview/` の React のプレビューのモジュール

## 目次

| ページ | 概要 |
| --- | --- |
| [components](./components/) | `frontend/src/features/overview/overview/components/` の React のプレビューのモジュール |
| [overview-screen.tsx](./overview-screen.tsx.yaml) | 画面設計『概要.tsx』のトップバーとタイルを描く。記録が読めないときは detail の行を出す |
| [queries.ts](./queries.ts.yaml) | 生成した queryOptions（記録・レビュー中のコメント・保存待ちの編集・スレッド）をまとめ、ルートの loader で先読みする |
| [search.ts](./search.ts.yaml) | 概要のルートの search params。`tab` は `overview` だけを受け、他の値と無い値は既定に落とす |
