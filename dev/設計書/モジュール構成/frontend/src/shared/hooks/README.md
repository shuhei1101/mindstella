# hooks

`frontend/src/shared/hooks/` の React のプレビューのモジュール

## 目次

<!-- table: data -->

| ページ | 概要 |
| --- | --- |
| [preview-queries.ts](./preview-queries.ts.yaml) | SPA が読む query（記録・レビュー中のコメント・保存待ちの編集・スレッド）と invalidate |
| [use-preview-search.ts](./use-preview-search.ts.yaml) | search の読み書き |
| [use-diff-view.ts](./use-diff-view.ts.yaml) | 差分の表示の時点と、項目ごとの印を返す |
| [use-edits.ts](./use-edits.ts.yaml) | 保存待ちの編集を溜める・取り消す・まとめて保存する mutation |
| [use-screen-filters.ts](./use-screen-filters.ts.yaml) | 画面の絞り込みの条件を URL と端末の保存領域で持つ（制約「保存した絞り込みの条件」） |
| [use-records.ts](./use-records.ts.yaml) | 記録に保存待ちの編集を重ねた索引を読む |
| [use-screen-edit.ts](./use-screen-edit.ts.yaml) | 一覧の画面の編集の入口を組む |
| [use-visible-kinds.ts](./use-visible-kinds.ts.yaml) | 表示する種類を返す |
| [use-comments.ts](./use-comments.ts.yaml) | レビュー中の書き込みを溜める・書き換える・消す・まとめて送る mutation と、書きかけの保存 |
| [use-voice-input.ts](./use-voice-input.ts.yaml) | 文字起こしの可否の query と、コメント・返信の入力の録音・文字起こし・すぐ送るの props |

<!-- /table -->
