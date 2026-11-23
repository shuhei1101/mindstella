# 次の Sprint の 11 件をまとめて対応する（非機能要件テスト・結合テストの安定化・画面の修正・設定と文書の追従）

## 概要

利用者が、iPad で詳細パネルの幅を変えられ、ボードをドラッグで横にスクロールでき、選択中・ホバー・未読を見分けられる画面を使用できるようになる。あわせて、使用しない確認済みのボタンを削除し、ドロワーの絞り込みを戻る操作で戻せ、図の種類を設定の更新で書き換えられるようにし、非機能要件テスト・落ちる結合テスト・変更履歴のページを修正する。

## 背景

[Issue #681](https://github.com/shuhei1101/mindstella/issues/681) の束。次の Sprint の未着手の 11 件を 1 つの作業 PR で対応する。

<!-- table: {"kind": "data"} -->

| Issue | 背景 |
| --- | --- |
| [#494](https://github.com/shuhei1101/mindstella/issues/494) | [PR #492](https://github.com/shuhei1101/mindstella/pull/492) で追加した NFR-26『記録の更新とスレッドの操作の時間』を手で測っただけで、非機能要件テストの層（`tests/nfr/`）が無い |
| [#622](https://github.com/shuhei1101/mindstella/issues/622) | `docs/guide/変更履歴.md` は mdmark の記法を含むが `.md` のまま。AI Monitor の規約『マージ手順』が `.mark.md` と `.md` の在る方へ追記するようになった（shuhei1101/ai-monitor#3506） |
| [#676](https://github.com/shuhei1101/mindstella/issues/676) | 詳細パネルの幅の区切りの当たり判定が小さく、iPad の指で幅を変えにくい（利用者のコメント TH-1555） |
| [#680](https://github.com/shuhei1101/mindstella/issues/680) | `test_post_thread_id_link_action` が本文の文字を待った直後に ID のボタンを待たずに数え、まとめて流すと落ちることがある |
| [#639](https://github.com/shuhei1101/mindstella/issues/639) | mdmark の [PR #735](https://github.com/shuhei1101/mdmark/pull/735) で表の既定が「どの列も留めない」に変わり、`table.pin_default` で今までの動きを選べるようになった。結合テスト 4 件が先頭の列が留まる期待のまま develop で fail している |
| [#643](https://github.com/shuhei1101/mindstella/issues/643) | `test_normal_when_real_project_index` が実物の project-index の `SourceNotServedError`（スキーマのファイルが無い）で develop で fail する |
| [#650](https://github.com/shuhei1101/mindstella/issues/650) | ドロワーでの絞り込みと並べ替えの変更が URL を置き換えるだけで履歴に残らず、knowledge の規約『入力と文言』の履歴に追加する単位から外れている（[PR #649](https://github.com/shuhei1101/mindstella/pull/649) のレビューで報告） |
| [#651](https://github.com/shuhei1101/mindstella/issues/651) | `update_settings` で `mdmark.map.kinds` を書き換えると「書き換えられないキー」になり、判定フローチャートの種類を追加できない（話し合いの D-820） |
| [#669](https://github.com/shuhei1101/mindstella/issues/669) | React への置き換えの後、ボードをドラッグで横にスクロールできなくなった（利用者のコメント TH-1518） |
| [#671](https://github.com/shuhei1101/mindstella/issues/671) | React への置き換えの後、未読のマーカー・選択中・ホバーの色が薄く、コメントのマーカーの位置が見づらい（利用者のコメント TH-1531・TH-1535） |
| [#675](https://github.com/shuhei1101/mindstella/issues/675) | 利用者は項目の状態を完了にできるため、詳細パネルの確認済みのボタンを使用する場面が無い（話し合いの D-859） |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 子 Issue ごとの要望と終了の条件 |
| [プレビュー](./プレビュー.mark.md) | 画面の修正（#639・#650・#669・#671・#675・#676・#680）の計画書 |
| [サーバー](./サーバー.mark.md) | 設定の更新・確認済み・非機能要件テスト・結合テスト（#494・#643・#651・#675）の計画書 |
