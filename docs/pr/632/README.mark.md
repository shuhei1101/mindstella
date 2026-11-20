# 使用していないネットワークの画面と検討事項のマップを削除する

## 概要

利用者が使用していないネットワークの画面と検討事項のマップを、プレビューの画面と設計書・公開ドキュメント・テストから削除し、保守の対象から除外する。

## 背景

[Issue #542](https://github.com/shuhei1101/mindstella/issues/542) の要望（利用者のコメント TH-1122・検討事項 D-569）。

- 2 つの機能は利用者が全く使用しておらず、画面の修正・React への移行（[#365](https://github.com/shuhei1101/mindstella/issues/365)・[#371](https://github.com/shuhei1101/mindstella/issues/371)）・作り直し（[#481](https://github.com/shuhei1101/mindstella/issues/481)）のたびに保守の対象になっている
- ネットワークの見た目（`network_look`）は、ネットワークの画面だけが使用する表示の設定で、サーバーの `config.yaml` の `display` と、設定の更新・既定の書き換えの API が持つ
- この削除で [#145](https://github.com/shuhei1101/mindstella/issues/145)・[#146](https://github.com/shuhei1101/mindstella/issues/146) は不要になり、[#148](https://github.com/shuhei1101/mindstella/issues/148) の範囲からマップが除外される（タスク計画で判断済み）

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理 |
| [プレビュー](./プレビュー.mark.md) | 今の画面と React の画面からの 2 つの機能・導線・見た目・依存の削除の計画書 |
| [サーバー](./サーバー.mark.md) | 表示の設定 `network_look` の削除と、既存のワークスペースの移し替えの計画書 |
