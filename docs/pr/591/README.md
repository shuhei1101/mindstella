# 設定が latest のとき、画面が mdmark の develop の最新の配布物を遅れずに読み込み、画面の CSS で mdmark の部品を上書きしない

## 概要

利用者が、設定の mdmark のバージョンが `latest` のとき、MindStella の画面で mdmark の develop の最新の部品（表・差分・図）の見た目と動きのまま資料を参照できるようになる。

## 背景

[Issue #590](https://github.com/shuhei1101/mindstella/issues/590) の不具合。
[#550](https://github.com/shuhei1101/mindstella/pull/550)（起点 [#532](https://github.com/shuhei1101/mindstella/issues/532)）で、設定の `latest` を jsDelivr の `gh/shuhei1101/mdmark@develop` の URL で読み込むようにした。
jsDelivr はブランチを指す URL を CDN で 12 時間・ブラウザで 7 日までキャッシュするため、mdmark の develop の配布物を作成し直しても画面へ届かない（確認時は約 13 時間前の配布物）。
あわせて、画面の CSS が mdmark の部品の見た目と動きを上書きしている箇所がある。
[#398](https://github.com/shuhei1101/mindstella/issues/398)（`--mdmark-color-bg-opaque` の指定）はこの PR へ統合した。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [プレビュー](./プレビュー.md) | プレビューの計画書 |
| [サーバー](./サーバー.md) | サーバーの計画書 |
