# 289

幅 320px でもプレビューのトップバー以外の画面を横にスクロールさせず、見切れなく操作できるようにする（[PR #289](https://github.com/shuhei1101/mindstella/pull/289)・起点 [Issue #269](https://github.com/shuhei1101/mindstella/issues/269)）。
画面は、プレビューを 320 x 568 で開いた状態を静的に書き出したもの。
スタイルはプラグインの `tokens.css`・`style.css` を読み、この PR で足す規則を各画面の末尾の `<style id="mock-289">` に置く。

| 画面 | 中身 |
| --- | --- |
| [search](../../pages/search/289/index.md) | 全体の検索の「検索を閉じる」を窓の中に残す |
| [diagram-viewer](../../pages/diagram-viewer/289/index.md) | 図の拡大の上の帯の「本文へ戻る」を印だけにし、帯を 1 行に収める |
| [overview](../../pages/overview/289/index.md) | 概要のタイルの見出しの帯で「すべて表示」を次の行へ回す |
| [detail-panel](../../pages/detail-panel/289/index.md) | 詳細パネルの本文の長い URL・インラインコードを折り返す |
| [detail-full](../../pages/detail-full/289/index.md) | 詳細の全画面の本文の長い URL・インラインコードを折り返す |
