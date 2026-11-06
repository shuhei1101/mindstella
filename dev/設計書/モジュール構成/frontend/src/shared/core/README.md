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
| [markdown-decorate.ts](./markdown-decorate.ts.yaml) | 描いた Markdown の本文の見せ方（表の列の幅・固定・見出しの固定・しま模様・セクションの折りたたみ・コードブロックの札とコピー・Alert の見出し） |
| [minimap.ts](./minimap.ts.yaml) | 差分のミニマップの印の計算と操作 |
| [body-render.ts](./body-render.ts.yaml) | 本文の差分の描画（足した・消した塊・語の面・図の差分） |
| [side-by-side.ts](./side-by-side.ts.yaml) | 左右に並べた本文の差分の組み立て |
| [html-body-diff.ts](./html-body-diff.ts.yaml) | HTML の本文の差分の組み立て |
| [html-frame.ts](./html-frame.ts.yaml) | スクリプトを動かさない HTML の本文の枠の組み立て |
| [term-tips.ts](./term-tips.ts.yaml) | 本文の印のツールチップと、見出しへの送り・示す箇所 |
| [list-rows.ts](./list-rows.ts.yaml) | 一覧の行の絞り込み・並べ替え・ドロワーの条件の組み立て |
| [format.ts](./format.ts.yaml) | 日時と値の文字の組み立て |
| [dom-parts.ts](./dom-parts.ts.yaml) | mdmark が描いた本文の中へ足す要素の組み立て |
| [lock.ts](./lock.ts.yaml) | 注目の起点のロックの判定と鍵の震え |

<!-- /table -->
