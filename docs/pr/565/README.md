# スキルとプレイブックをやめて記録のエージェントフローにし、ゴール判定・次の候補などの削除する機能を削除する

## 概要

MindStella のセッションのエージェントが、スキルとプレイブックではなく、プラグインに同梱して project-index で配信するエージェントフロー（起動と再開・コメントの取り込み・記録の使い分け）に従って記録する。
話し合いの進め方とゴールに依存する機能（ゴール判定・次の候補・リリース・フェーズ・対象とカテゴリーなど）を削除する。

## 背景

[Issue #518](https://github.com/shuhei1101/mindstella/issues/518) の要望で、MindStella を project-index と同じ作りに作り直す束 [Issue #481](https://github.com/shuhei1101/mindstella/issues/481) の子のうち 3 つ目（資料 A-107 の「シナリオを作る順」の No 3）。

- 今は setup・session・upgrade のスキルと、プレイブック（`playbooks/`）・手引き（`references/`）が、話し合いの進め方（ヒアリング・リサーチ・方針転換・範囲の見直し・ゴール判定）を持つ。MindStella を、利用者とやり取りするインターフェースだけを持つ project-index の拡張にする方針（D-269 C）で、進め方とゴールは導入する側に任せる（D-261・D-262）
- No 1（[PR #531](https://github.com/shuhei1101/mindstella/pull/531)）で MindStella の API と MindStella のセッションができ、SessionStart のフックが進め方の文書の場所を注入する。No 2（[PR #540](https://github.com/shuhei1101/mindstella/pull/540)）で記録の検索と書き込みが project-index へ移り、検討事項の `depends_on`・`parent` は `related` の `{to, type}` になった
- 削除の候補の「要判断」は D-275〜D-278 で決定済み（A-107 の `## 削除の候補`）
- 起票の後に、スレッドで利用者に回答を求める「要返信」をやめ、回答が要ることは全て検討事項に挙げる決定（D-481）と、記録の種類ごとの使い方のガイドを追加する決定（D-502）が [Issue のコメント](https://github.com/shuhei1101/mindstella/issues/518#issuecomment-6879594509) に追記された

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [スキル](./スキル.md) | スキル・プレイブック・手引きの削除と、エージェントフローの新規作成の計画書 |
| [プラグイン](./プラグイン.md) | SessionStart の注入とエージェントフローの配信の計画書 |
| [サーバー](./サーバー.md) | 削除するツール・キーと、読み込みのときの移し替えの計画書 |
| [プレビュー](./プレビュー.md) | 概要・検討事項のマップ・資料・設定の画面の計画書 |
