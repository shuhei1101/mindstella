# stores

`frontend/src/shared/stores/` の React のプレビューのモジュール

## 目次

| ページ | 概要 |
| --- | --- |
| [connection-store.ts](./connection-store.ts.yaml) | 書き換えの知らせがつながっているか（インターフェース定義『SPAを開く』の制約「接続の状態」） |
| [theme-store.ts](./theme-store.ts.yaml) | 今の画面と同じキー。値の JSON の `theme` だけを読み書きし、他のキーは残す |
| [prefs-store.ts](./prefs-store.ts.yaml) | 表の列・ピン留め・差分のミニマップ・本文の差分の並べ方・本文の見せ方・絞り込みの条件を、今の画面と同じ `localStorage` のキーで読み書きする（制約「端末の保存領域」） |
