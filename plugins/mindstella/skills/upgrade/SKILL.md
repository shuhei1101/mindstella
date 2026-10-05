---
name: upgrade
description: プラグインを上げた後、ワークスペースの版が古いと案内されたときに、ワークスペースの版とプラグインの版を比べ、版ごとの手順を当てて今の版へ移し替えるスキル
argument-hint: "[ワークスペースのフォルダ]"
allowed-tools: Read, mcp__mindstella__migrate, mcp__mindstella__check
---

# upgrade

ワークスペースの版とプラグインの版を比べ、版ごとの手順を当てて今の版へ移し替える。
写しを取る・手順を当てる・値を入れる・版を書き換えるは `migrate` が行い、このスキルが自分でファイルを書くことはない。

## 入力

- ワークスペースのフォルダ: $ARGUMENTS
  - 空ならフォルダの指定を尋ねて終える
  - `{ワークスペースのフォルダ}/config.yaml` か `mindmap.yaml` を Read で読めないときは、何も書き込まず `/mindstella:setup` を案内して終える

## ステップ

上から順に進む。

| ステップ | 手順 |
| --- | --- |
| ツールの確認 | mindstella の MCP のツール（`mcp__mindstella__migrate`・`check`）があるかを見る。無ければ、ワークスペースに何も書かず、起動スクリプト（`{プラグインのフォルダ}/bin/mindstella {ワークスペースのフォルダ}`）で立ち上げ直すよう案内して止まる（以降は実行しない）。依存は起動スクリプトが確かめる |
| 版の比較 | `migrate` を `plan: true` で呼び、結果の `relation` を読む。`same` なら移し替えるものが無いと示して終える。`newer` ならプラグインを更新するよう案内して止まる（以降は実行しない） |
| 手順の一覧 | 結果の `steps` を版の順に、`version` と `summary` で示す。`destructive` が `true` の手順があるときだけ、当ててよいかを利用者に確かめる（利用者が断ったら止まる） |
| 手順を当てる | `migrate`（`plan` なし）を呼ぶ。ツールのエラーが返ったら、本文の失敗した版・手順・理由を示して止まる（`migrate` が写しから戻している）。結果の `backup` が写しの場所になる |
| 点検 | `check` を呼ぶ。`migrate` の結果の `needs_values` のキーだけを、`description` を添えて利用者に聞き、答えを `migrate` の `values` で入れる。`needs_values` のキー以外の問題が出たときは、示して止まる |
| 版の書き換え | `migrate` を `record: true` で呼ぶ。ツールのエラーが返ったら、本文の合わない箇所を示して止まる |
| 仕上げ | 結果の `recorded` の版と、`backup` の写しの場所を示し、`/mindstella:session {ワークスペースのフォルダ}` で続けるよう案内する |

## ツール

どれも mindstella の MCP のツール（`mcp__mindstella__{ツール}`）で、`workspace` にワークスペースのフォルダを渡す。
スクリプトを Bash で起動しない。

| ツール | 使う引数 |
| --- | --- |
| `migrate`（版を比べる） | `workspace`・`plan: true` |
| `migrate`（手順を当てる） | `workspace` |
| `migrate`（値を入れる） | `workspace`・`values`（値が要るキーごとに `file`・`key`・`value` を持つオブジェクトの配列） |
| `migrate`（版を書き換える） | `workspace`・`record: true` |
| `check` | `workspace` |
