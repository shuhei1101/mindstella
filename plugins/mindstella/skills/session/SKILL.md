---
name: session
description: セットアップの後に、ワークスペースの話し合いを進めるとき。発言の取り込み・ヒアリング・リサーチ・方針転換・範囲の見直し・プレビュー・ゴール判定を場面に応じて回し、ゴールまで進める
argument-hint: "[ワークスペースのフォルダ]"
allowed-tools: Read, Agent, WebSearch, WebFetch, mcp__mindstella__add, mcp__mindstella__update, mcp__mindstella__remove, mcp__mindstella__update_settings, mcp__mindstella__adopt, mcp__mindstella__edit_option, mcp__mindstella__batch, mcp__mindstella__changes_since_read, mcp__mindstella__commit, mcp__mindstella__pending, mcp__mindstella__status, mcp__mindstella__next, mcp__mindstella__impact, mcp__mindstella__find, mcp__mindstella__show, mcp__mindstella__attrs, mcp__mindstella__tags, mcp__mindstella__check, mcp__mindstella__goal, mcp__mindstella__migrate, mcp__mindstella__clear_release, mcp__mindstella__export, mcp__mindstella__preview_url, mcp__mindstella__readme, mcp__mindstella__threads, mcp__mindstella__thread, mcp__mindstella__new_thread, mcp__mindstella__reply, mcp__mindstella__set_thread_status, mcp__mindstella__update_thread
---

# session

作成済みのワークスペースで、利用者の発言を記録しながら、ゴールまで話し合いを進める。

## 入力

- ワークスペースのフォルダ: $ARGUMENTS
  - 空なら、同じ会話で `/mindstella:setup` が渡したフォルダを使う。それも無ければ `/mindstella:setup` を案内して終える
  - `{ワークスペースのフォルダ}/.mindstella/config.yaml` か、直下の `config.yaml`・`mindmap.yaml` を Read で読めないときは、何も書き込まず `/mindstella:setup` を案内して終える

## ステップ

発言のたびに、場面に合うステップを選ぶ。

| ステップ | 手順 | 実行する場面 |
| --- | --- | --- |
| 準備 | mindstella の MCP のツール（`mcp__mindstella__add` など）があるかを見る。無ければ、ワークスペースに何も書かず、起動スクリプト（`{プラグインのフォルダ}/bin/mindstella {ワークスペースのフォルダ}`）で立ち上げ直すよう案内して止まる。あれば `{ワークスペースのフォルダ}/.mindstella/config.yaml`（無ければ直下の `config.yaml` か `mindmap.yaml`）を Read で読み、`migrate` を `plan: true` で呼ぶ。結果の `relation` が `older` なら何も書き込まず `/mindstella:upgrade {フォルダ}` を案内して止まり、`newer` ならプラグインを更新するよう案内して止まる。`same` のときだけ、`readme` を呼んでワークスペースの直下の README を書き直す（`written` が偽でも利用者には示さずに続ける。ツールのエラーは本文を利用者に短く示して準備を続ける）。続けて `playbooks` に並んだ進め方ガイドをすべて（`${CLAUDE_PLUGIN_ROOT}/skills/mindmap/playbooks/{プレイブック}.md`）Read で読み、続けて `changes_since_read` を呼ぶ。`had_read_point` が偽なら何も示さない。`added`・`changed`・`removed` があれば、前回読んだ後に足された・変わった・消された項目として、ID・タイトル・変わったキーと読んだ時点の値（`before`）を短く示し、話し合いの前提にする。利用者が画面で足した項目（`updated_by` が `user`）と変えた項目（`by` に `user` を含む）は、利用者が画面で変えた分として AI の変更と分けて示す。続けて `threads` を `awaiting: true` で呼ぶ（状態は渡さず、オープンもクローズも拾う）。1 件以上あれば、スレッド 1 件ずつ、`thread` で未読の書き込みを読み、利用者に示す。示すとき、箇所（`loc`）を持つスレッドには本文の行の範囲か値のキーと選んだ文を添え、`target` が `null` のスレッドには項目を指さない旨を添える。続けて取り込みのステップで記録してから、「スレッドの返し方」に沿って返信するかクローズにする。`loc` を持つスレッドはその箇所への意見として、項目を指さないスレッドは発言と同じく対象を振り分けて記録する。0 件ならスレッドの取り込みを飛ばす。取り込みの前に `pending` を呼び、空でなければ、前の話し合いでまとめ忘れた分として説明を付けて `commit` する | 話し合いの最初の 1 回 |
| スレッドの取り込み | 利用者の発言としては取り込まず、入力された文字列の中身も記録に使わない。`threads` を `awaiting: true` で呼び、一覧にあるスレッドだけを、準備のときと同じく 1 件ずつ取り込みのステップで記録してから、「スレッドの返し方」に沿って返信するかクローズにする。0 件なら何も記録しない | 話し合いの途中に `[mindstella]` で始まる 1 行が入力された |
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
設定（`.mindstella/config.yaml`）の書き換え・リサーチの起動前の確認・ゴール判定の確定は記録の書き込みに含めず、それぞれのステップの確かめを残す。
資料・調査を `add` で足すときは、本文や会話でその項目を呼ぶ名前（タイトルと違う言い方）を `aliases` に、タイトルだけでは中身が分からないときは中身を表す短い文を `description` に書く。
呼び名が増えた・変わったときは `update` で直す。タグ（`tags`）には入れない。
記録を直して `commit` が `id` を返した後、利用者への応答・ワークスペースの外（Issue のスレッドなど）に直したことを書くときは、その `id` を `diff` に渡して `preview_url` を呼び、返った `url` をリンクとして添える。
記録の本文（会話ログ・メモ・資料など）とワークスペースの中のスレッド（`reply`・`new_thread`）に書くときは `preview_url` を呼ばず、`[文言](#diff={id})` のリンクを書く。
`commit` の `id` が `null` のときはどちらも添えない。

## スレッドの返し方

利用者のコメントは、スレッドとして届く。

- 質問・依頼には `reply` で返信する（要約の書き直しと、読んだ利用者の書き込みの取り込み済みを 1 回で行う）。足した・直した項目があれば、その ID を返信に書く。返信してもクローズにしない
- クローズのスレッドへ返信が要るときは、先に `set_thread_status` で理由つきでオープンに戻す
- 返事の要らない書き込み（「了解」など）には返信しない。話が済んでいれば `set_thread_status` で理由つきでクローズにし、`update_thread`（`take: true`・要約）で取り込み済みにする
- `thread` で読んだだけでは取り込み済みにならない
- 取り込み待ちのスレッドのほかは、既定でオープンのスレッドの未読だけを読む。過去の経緯が要るときだけ `threads` を `status: closed` か `all` で、`thread` を `unread_only: false` で呼ぶ。一覧はキーだけで引き、要約で読むかを決める
- ワークスペースの外へ書き込む前の確認（Issue の起票 など）と、話の流れと関係の無い知らせは、`new_thread` で本文・要約・タグを渡してスレッドを立て、返事が届くまで外へは書き込まない。今の話の流れの中で答えが要る問い（ヒアリング・方針転換の確認・リサーチを始めてよいか）はターミナルで聞く。立てられなかったときは同じことをターミナルで聞く。タグは記録の話題のタグと同じく `tags` の語彙から選び、合うタグが無ければ語彙へ登録してから付ける

## ツール

どれも mindstella の MCP のツール（`mcp__mindstella__{ツール}`）で、`workspace` にワークスペースのフォルダを渡す。
スクリプトを Bash で起動しない。
ツールが書き換えた記録は、サーバーが開いている画面へ知らせるため、書いた後に書き出しを流さない。

| ツール | 使う引数 |
| --- | --- |
| `add` | `workspace`・`kind`（`decision`・`task`・`research`・`doc`・`term`・`note`・`log`）・`item`（項目の JSON のオブジェクト。`id`・`created`・`updated`・`updated_by`・`body` は渡さない。本文はどの種類も `body_markdown`。資料は `body_html` で HTML の本文も書ける） |
| `update` | `workspace`・`id`・`item`（置き換えるキーのオブジェクト。消すキーは `null`） |
| `remove` | `workspace`・`id`（消す項目。ほかの記録が指しているとエラーで、指している記録の行が返る） |
| `update_settings` | `workspace`・`settings`（置き換える設定のキーのオブジェクト。`summary`・`description`・`playbooks`・`phases`・`target_label`・`goal`・`targets`・`categories`・`tags`（`name` と任意の `summary` を持つ語彙の配列）・`links`・`history_limit` だけ。`description`・`goal`・`tags`・`links`・`history_limit` は `null` で消す）・`phase_map`・`target_map`・`category_map`・`tag_map`（任意。`phases`・`targets`・`categories`・`tags` を変えるときだけ、新しい設定に無い古い名前 → 新しい名前の対応。`tag_map` は値を `null` にするとタグを外す） |
| `adopt` | `workspace`・`id`（検討事項）・`key`（採用する案の記号）。状態が `決定済み` になる |
| `edit_option` | `workspace`・`id`（検討事項）・`action`（`add`・`update`・`remove`）・`key`（案の記号）・`option`（`add`・`update` の案の中身のオブジェクト。`content`・`pros`・`cons`・`note`・`reason`・`recommended`。`recommended: true` で推奨の印を立てる（ほかの案の印は外れる）。`update` で消すキーは `null`。`remove` では渡さない） |
| `batch` | `workspace`・`operations`（操作の配列。要素は `op`（`add`・`update`・`show`）と、`add` は `kind`・`item`、`update` は `id`・`item`、`show` は `id`。同じ呼び出しで先に足した項目は `$番号`（`add` の番号、1 始まり）で指す） |
| `changes_since_read` | `workspace` |
| `commit` | `workspace`・`summary`（このまとまりで何をしたかの一言の説明。1〜200 文字） |
| `pending` | `workspace` |
| `next` | `workspace`・`limit`（任意） |
| `impact` | `workspace`・`id` |
| `find` | `workspace`・`text`・`kind`・`status`・`tags`（全てを持つ。AND）・`any_tags`（いずれかを持つ。OR）・`target`・`category`・`phase`・`attr`（`名前=値` の配列）・`limit`（1 ページの件数。既定 20）・`cursor`（前のページの `next_cursor`）・`response_format`（`concise`・`detailed`）。条件は全て任意。タグは語彙のタグだけ |
| `show` | `workspace`・`id` |
| `attrs` | `workspace` |
| `tags` | `workspace` |
| `migrate` | `workspace`・`plan: true` |
| `status` | `workspace` |
| `check` | `workspace` |
| `export` | `workspace`・`out` |
| `goal` | `workspace` |
| `clear_release` | `workspace` |
| `preview_url` | `workspace`・`diff`（任意。差分を開くまとまりの ID） |
| `readme` | `workspace` |
| `threads` | `workspace`・`status`（任意。`open`・`closed`・`all`）・`tag`（任意）・`unread`（任意）・`awaiting`（任意） |
| `thread` | `workspace`・`id`（スレッドの ID）・`unread_only`（任意。既定は真） |
| `new_thread` | `workspace`・`body`・`summary`・`tags`（任意）・`target`（任意。向ける項目の ID） |
| `reply` | `workspace`・`id`・`body`・`summary`・`take`（任意。既定は真） |
| `set_thread_status` | `workspace`・`id`・`status`（`open`・`closed`）・`reason`（任意） |
| `update_thread` | `workspace`・`id`・`summary`（任意）・`tags`（任意）・`take`（任意） |
