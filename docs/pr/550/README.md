# 画面が読み込む mdmark のバージョンを設定で指定できるようにし、既定を latest にする

## 概要

利用者が、MindStella を更新しなくても、mdmark の develop へ入った新しい機能（map の図・JSON のマーカー）をプレビューの画面で使えるようになる。
バージョンを固定したいときは、設定でタグを指定できる。

## 背景

[Issue #532](https://github.com/shuhei1101/mindstella/issues/532) の要望（話し合いの決定 D-505）。

- プレビューの雛形・React の画面・配る書き出しは、mdmark を `v0.8.0` のタグに固定し、`integrity` で中身を確かめて読む。mdmark の最新のタグは `v0.13.0` で、map（[mdmark#324](https://github.com/shuhei1101/mdmark/issues/324)）と JSON のマーカー（[mdmark#451](https://github.com/shuhei1101/mdmark/issues/451)）は `v0.8.0` に無い。flow・sequence は廃止され、map へ変換するスクリプトがある（[mdmark#534](https://github.com/shuhei1101/mdmark/issues/534)）
- mdmark を上げるたびにタグと `integrity` を書き換える Issue（[#475](https://github.com/shuhei1101/mindstella/issues/475)・[#483](https://github.com/shuhei1101/mindstella/issues/483)）が要った。この 2 件と、ワークスペースの文書の移し替え（[#512](https://github.com/shuhei1101/mindstella/issues/512) から移した分）をこの PR に統合する（[扱いの判断](https://github.com/shuhei1101/mindstella/issues/532#issuecomment-6879952440)）
- mdmark を参照する全てのリポジトリで同じ切り替えを行い、mdmark の側（[mdmark#620](https://github.com/shuhei1101/mdmark/issues/620)）で develop の最新を参照できることを確かめてから切り替える（[利用者の指示](https://github.com/shuhei1101/mindstella/issues/532#issuecomment-6916041488)）

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [プレビュー](./プレビュー.md) | 雛形・React の画面・Storybook が読む mdmark の版を設定から決める計画書 |
| [サーバー](./サーバー.md) | 設定のキー・配信と配る書き出しの読み込み・ワークスペースの移し替えの計画書 |
