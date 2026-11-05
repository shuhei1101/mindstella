# hooks

`frontend/src/shared/hooks/` の React のプレビューのモジュール

## 目次

| ページ | 概要 |
| --- | --- |
| [preview-queries.ts](./preview-queries.ts.yaml) | SPA が読む query（記録・レビュー中のコメント・保存待ちの編集・スレッド）と invalidate |
| [use-preview-search.ts](./use-preview-search.ts.yaml) | search の読み書き |
| [use-diff-view.ts](./use-diff-view.ts.yaml) | 差分の表示の時点と、項目ごとの印を返す |
| [use-edits.ts](./use-edits.ts.yaml) | 保存待ちの編集を溜める・取り消す・まとめて保存する mutation |
| [use-screen-filters.ts](./use-screen-filters.ts.yaml) | 画面の絞り込みの条件を URL と端末の保存領域で持つ（制約「保存した絞り込みの条件」） |
