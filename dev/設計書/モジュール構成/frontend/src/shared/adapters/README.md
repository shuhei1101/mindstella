# adapters

`frontend/src/shared/adapters/` の React のプレビューのモジュール

## 目次

| ページ | 概要 |
| --- | --- |
| [api-client.ts](./api-client.ts.yaml) | orval の mutator。fetch で呼び、成功は本文と status を返し、失敗は AppError を投げる |
| [events-client.ts](./events-client.ts.yaml) | インターフェース定義『書き換えの知らせ』 |
| [libraries.ts](./libraries.ts.yaml) | 描画のライブラリ（mdmark・mermaid・elkjs・marked・jsdiff）を、今の画面と同じ配信元と版から `integrity` で確かめて読む（制約「描画のライブラリ」） |
