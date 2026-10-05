---
name: session
description: セットアップの後に、ワークスペースの話し合いを進めるとき。発言の取り込み・ヒアリング・リサーチ・方針転換・範囲の見直し・プレビュー・ゴール判定を場面に応じて回し、ゴールまで進める
argument-hint: "[ワークスペースのフォルダ]"
allowed-tools: Read, Agent, WebSearch, WebFetch, mcp__mindstella__add, mcp__mindstella__update, mcp__mindstella__update_settings, mcp__mindstella__adopt, mcp__mindstella__edit_option, mcp__mindstella__batch, mcp__mindstella__changes_since_read, mcp__mindstella__commit, mcp__mindstella__pending, mcp__mindstella__status, mcp__mindstella__next, mcp__mindstella__impact, mcp__mindstella__find, mcp__mindstella__show, mcp__mindstella__attrs, mcp__mindstella__check, mcp__mindstella__goal, mcp__mindstella__migrate, mcp__mindstella__clear_release, mcp__mindstella__export, mcp__mindstella__preview_url, mcp__mindstella__submissions, mcp__mindstella__take_submission
---

# session

作成済みのワークスペースで、利用者の発言を記録しながら、ゴールまで話し合いを進める。

## 入力

- ワークスペースのフォルダ: $ARGUMENTS
  - 空なら、同じ会話で `/mindstella:setup` が渡したフォルダを使う。それも無ければ `/mindstella:setup` を案内して終える
  - `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読めないときは、何も書き込まず `/mindstella:setup` を案内して終える

## ステップ

発言のたびに、場面に合うステップを選ぶ。

| ステップ | 手順 | 実行する場面 |
| --- | --- | --- |
| 準備 | mindstella の MCP のツール（`mcp__mindstella__add` など）があるかを見る。無ければ、ワークスペースに何も書かず、起動スクリプト（`{プラグインのフォルダ}/bin/mindstella {ワークスペースのフォルダ}`）で立ち上げ直すよう案内して止まる。あれば `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読み、`migrate` を `plan: true` で呼ぶ。結果の `relation` が `older` なら何も書き込まず `/mindstella:upgrade {フォルダ}` を案内して止まり、`newer` ならプラグインを更新するよう案内して止まる。`same` のときだけ、`playbooks` に並んだ進め方ガイドをすべて（`${CLAUDE_PLUGIN_ROOT}/skills/mindmap/playbooks/{プレイブック}.md`）Read で読み、続けて `changes_since_read` を呼ぶ。`had_read_point` が偽なら何も示さない。`added`・`changed` があれば、前回読んだ後に足された・変わった項目として、ID・タイトル・変わったキーと読んだ時点の値（`before`）を短く示し、話し合いの前提にする。続けて `submissions` を呼ぶ。1 件以上あれば、届いていた送信（ID・`target`・`target_title`・`body`・`loc`）を示す。`loc` を持つ送信には本文の行の範囲か値のキーと選んだ文を添え、`target` が `null` の送信には項目を指さない旨を添える。送った順に 1 件ずつ、取り込みのステップで記録してから `take_submission` で取り込み済みにする。`loc` を持つ送信はその箇所への意見として、項目を指さない送信は発言と同じく対象を振り分けて記録する。0 件なら取り込みを飛ばす。取り込みの前に `pending` を呼び、空でなければ、前の話し合いでまとめ忘れた分として説明を付けて `commit` する | 話し合いの最初の 1 回 |
| 取り込み | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/取り込み.md` | 利用者が発言した（決め事・問い・やること・保留・中止・図や文書・脱線した質問） |
| ヒアリング | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/ヒアリング.md` | 取り込みの後に前提が揃った未決定がある、または利用者が次に決めることを求めた |
| リサーチ | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/リサーチ.md` | 外部ライブラリ・外部 API を決める検討事項が積まれた、進め方ガイドの「必ず調べるもの」に当たった、または利用者が調べるよう頼んだ |
| 方針転換 | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/方針転換.md` | 利用者が決定済みの検討事項の案を変える、またはスコープが変わって納品物が要らなくなった |
| 範囲の見直し | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/範囲の見直し.md` | 話の範囲が広がった、利用者が題名・話し合いの概要・ゴール・進め方ガイド・最上位の軸の呼び名・対象・カテゴリーを変えたいと言った、話の中身と呼び名が合わなくなった、またはゴール判定でゴールが無く利用者が決めると言った |
| プレビュー | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/プレビュー.md` | 利用者が記録を見たいと言った、または人に渡したいと言った |
| ゴール判定 | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/ゴール判定.md` | 利用者がゴールに届いたかを尋ねた、または `next` の候補が無くなった |

## 記録の書き方

記録（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）は、状況が変わるたびに利用者に確かめずに足し、書き換える。
利用者に確かめるのは、GitHub への起票などワークスペースの外へ書き込むときだけ。
設定（`mindmap.yaml`）の書き換え・リサーチの起動前の確認・ゴール判定の確定は記録の書き込みに含めず、それぞれのステップの確かめを残す。

## ツール

どれも mindstella の MCP のツール（`mcp__mindstella__{ツール}`）で、`workspace` にワークスペースのフォルダを渡す。
スクリプトを Bash で起動しない。
ツールが書き換えた記録は、サーバーが開いている画面へ知らせるため、書いた後に書き出しを流さない。

| ツール | 使う引数 |
| --- | --- |
| `add` | `workspace`・`kind`（`decision`・`task`・`research`・`doc`・`term`・`note`・`log`）・`item`（項目の JSON のオブジェクト。`id`・`created`・`updated`・`body` は渡さない。本文は `body_markdown`） |
| `update` | `workspace`・`id`・`item`（置き換えるキーのオブジェクト。消すキーは `null`） |
| `update_settings` | `workspace`・`settings`（置き換える設定のキーのオブジェクト。`summary`・`description`・`playbooks`・`phases`・`target_label`・`goal`・`targets`・`categories`・`links`・`history_limit` だけ。`description`・`goal`・`links`・`history_limit` は `null` で消す）・`phase_map`・`target_map`・`category_map`（任意。`phases`・`targets`・`categories` を変えるときだけ、新しい設定に無い古い名前 → 新しい名前の対応） |
| `adopt` | `workspace`・`id`（検討事項）・`key`（採用する案の記号） |
| `edit_option` | `workspace`・`id`（検討事項）・`action`（`add`・`update`・`remove`）・`key`（案の記号）・`option`（`add`・`update` の案の中身のオブジェクト。`content`・`pros`・`cons`・`note`・`reason`。`update` で消すキーは `null`。`remove` では渡さない） |
| `batch` | `workspace`・`operations`（操作の配列。要素は `op`（`add`・`update`・`show`）と、`add` は `kind`・`item`、`update` は `id`・`item`、`show` は `id`。同じ呼び出しで先に足した項目は `$番号`（`add` の番号、1 始まり）で指す） |
| `changes_since_read` | `workspace` |
| `commit` | `workspace`・`summary`（このまとまりで何をしたかの一言の説明。1〜200 文字） |
| `pending` | `workspace` |
| `next` | `workspace`・`limit`（任意） |
| `impact` | `workspace`・`id` |
| `find` | `workspace`・`text`・`kind`・`status`・`tag`・`target`・`category`・`phase`・`attr`（`名前=値` の配列）。条件は全て任意 |
| `show` | `workspace`・`id` |
| `attrs` | `workspace` |
| `migrate` | `workspace`・`plan: true` |
| `status` | `workspace` |
| `check` | `workspace` |
| `export` | `workspace`・`out` |
| `goal` | `workspace` |
| `clear_release` | `workspace` |
| `preview_url` | `workspace` |
| `submissions` | `workspace` |
| `take_submission` | `workspace`・`id`（送信の ID） |
