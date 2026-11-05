# core

`frontend/src/shared/core/` の React のプレビューのモジュール

## 目次

<!-- table: data -->

| ページ | 概要 |
| --- | --- |
| [app-error.ts](./app-error.ts.yaml) | 失敗した応答から作るエラー。`detail` を画面に出す |
| [legacy-url.ts](./legacy-url.ts.yaml) | React に無い画面を開くときの今の画面（インターフェース定義『プレビューの配信』） |
| [preview-search.ts](./preview-search.ts.yaml) | SPA の search params（インターフェース定義『SPAを開く』の request）の Zod スキーマと、記録に合わない値を外す処理、今の画面へ写すハッシュ |
| [records.ts](./records.ts.yaml) | 記録の型・索引・関係する項目（今の画面の `core/records.ts` と同じ振る舞い） |
| [filters.ts](./filters.ts.yaml) | 画面ごとの絞り込みの条件を行に当てる計算 |
| [diff.ts](./diff.ts.yaml) | 差分の表示の計算（今の画面の `core/diff.ts` と同じ振る舞い |
| [edits.ts](./edits.ts.yaml) | 保存待ちの編集を記録に重ねる計算（今の画面の `core/edits.ts` と同じ振る舞い） |
| [doc-export.ts](./doc-export.ts.yaml) | 資料のエクスポートの HTML と Markdown の組み立て（今の画面の `core/doc-export.ts` と同じ振る舞い） |
| [body-links.ts](./body-links.ts.yaml) | 描いた本文に、見出しのリンク・本文の印・項目の ID のリンクを付ける処理（今の画面の `core/libs.ts` の `linkHeadings`・`linkBody` と同じ振る舞い） |

<!-- /table -->
