# 結合テスト test_option_draft_when_redrawn を、入力欄にカーソルがある間は描き直さない今の振る舞いに合わせる

## 概要

結合テスト `tests/integration/preview/test_detail_panel_screen.py::test_option_draft_when_redrawn` を、develop で pass させる。

## 背景

[Issue #579](https://github.com/shuhei1101/mindstella/issues/579) の不具合。[PR #565](https://github.com/shuhei1101/mindstella/pull/565) の結合テスト作成で見つかった。
テストは「案を追加」の入力欄にカーソルがあるまま書き換えの通知を出させ、編集の表示のフォームが描き直されるのを 10 秒待って打ち切られる。
[PR #557](https://github.com/shuhei1101/mindstella/pull/557) で、入力欄にカーソルがある間は記録の更新を画面に反映せず、離れたときに 1 回だけ描き直す振る舞いにしたため、テストの期待と食い違っている。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理・変更箇所の由来 |
| [プレビュー](./プレビュー.md) | 原因と、結合テストの修正方針・テスト結果 |
