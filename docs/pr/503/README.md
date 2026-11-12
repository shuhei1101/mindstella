# スレッドから一覧へ戻ったとき、開いていた行へ確実にフォーカスを戻す

## 概要

React のプレビューのコメントの一覧で、スレッドから「一覧へ戻る」（または入力欄の外の Esc）で戻ったとき、描き直しより先に次のコマが来ても、開いていた行へフォーカスを戻す。

## 背景

[Issue #497](https://github.com/shuhei1101/mindstella/issues/497) の報告。
`comments-panel.tsx` の `backToList` は、一覧の描き直しを待たずに `requestAnimationFrame` で行を探して `focus()` するため、行がまだ無いとフォーカスが `body` に落ちる。
[PR #496](https://github.com/shuhei1101/mindstella/pull/496) で同じ型の `thread-view.tsx` の `closeReason` を修正した際に見つかり、スコープ外にした。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [プレビュー](./プレビュー.md) | コメントの一覧の画面と単体・結合テストの計画書 |
