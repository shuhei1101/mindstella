"""結合テストが記録を project-index の `write_docs` と同じ書き方で書き換え、変更の検知に変更履歴を積ませる関数。

ID は `next_id` で取り、種類ごとの YAML と本文のファイルを一時ファイルに書いて置き換える。書き換えは
MindStella のセッションの応答の途中として行い、変更の検知が `ai` の変更として記録するまで待つ
（`McpServer.write_as_ai`）。
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import KIND_FILES, McpServer, ToolResult

# 項目に渡すと本文のファイルに書く、本文の原文のキー → 本文のファイルの拡張子
BODY_KEYS = {"body_markdown": ".md", "body_html": ".html"}


def server_of(call_tool: Callable[..., ToolResult]) -> McpServer:
    """fixture `call_tool`（`McpServer.call`）から、ツールを呼ぶ常駐サーバーを返す。"""
    server = getattr(call_tool, "__self__", None)
    assert isinstance(server, McpServer), "call_tool は McpServer.call を渡してください"
    return server


def write_items(
    call_tool: Callable[..., ToolResult],
    workspace: str,
    *,
    add: Sequence[tuple[str, Mapping[str, Any]]] = (),
    update: Mapping[str, Mapping[str, Any]] | None = None,
    remove: Sequence[str] = (),
) -> list[str]:
    """項目を足す・直す・消す書き換えを 1 回で書き、変更の検知が記録し終えるまで待って、足した項目の ID を返す。

    add は (種類, 項目) の並び、update は ID → 重ねるキー、remove は消す ID の並び。項目の
    `body_markdown`・`body_html` は `docs/{ID}.md`・`docs/{ID}.html` に書き、項目の `body` にそのパスを入れる。
    """
    new_ids = [_next_id(call_tool, workspace, kind) for kind, _ in add]

    def _change(records: Path) -> None:
        files: dict[str, list[dict[str, Any]]] = {}
        texts: dict[Path, str | None] = {}

        def _items(item_id: str) -> list[dict[str, Any]]:
            """ID の種類の YAML の items を、1 回だけ読んで返す。"""
            name = KIND_FILES[item_id[0]]
            if name not in files:
                path = records / name
                loaded = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
                files[name] = list((loaded or {}).get("items", []))
            return files[name]

        # 足す: 取った ID を付けて末尾に並べる
        for item_id, (_kind, item) in zip(new_ids, add, strict=True):
            _items(item_id).append(_with_body({"id": item_id, **item}, records, texts))
        # 直す: 渡したキーを重ねる
        for item_id, changes in (update or {}).items():
            items = _items(item_id)
            index = next(index for index, item in enumerate(items) if item["id"] == item_id)
            items[index] = _with_body({**items[index], **changes}, records, texts)
        # 消す: 項目と本文のファイルを消す
        for item_id in remove:
            items = _items(item_id)
            removed = next(item for item in items if item["id"] == item_id)
            items.remove(removed)
            if "body" in removed:
                texts[records / removed["body"]] = None
        for name, items in files.items():
            texts[records / name] = yaml.safe_dump(
                {"items": items}, allow_unicode=True, sort_keys=False
            )
        # 本文を先に、種類ごとの YAML を後に置き換える（write_docs と同じく 1 ファイルずつ置き換える）
        for path, text in sorted(texts.items(), key=lambda entry: entry[0].suffix == ".yaml"):
            _replace(path, text)

    server_of(call_tool).write_as_ai(Path(workspace), _change)
    return new_ids


def write_tool(call_tool: Callable[..., ToolResult], name: str, **arguments: Any) -> ToolResult:
    """`add`・`update`・`remove` を記録の書き換え（write_items）にし、それ以外はツールを呼んで結果を返す。

    `add` は `kind`・`item`、`update` は `id`・`item`、`remove` は `id` を受け、結果の `data` に `{"id": 項目の ID}` を入れる。
    """
    workspace = arguments["workspace"]
    # 項目を足す: next_id で取った ID を返す
    if name == "add":
        item_id = write_items(call_tool, workspace, add=[(arguments["kind"], arguments["item"])])[0]
    # 項目を直す
    elif name == "update":
        write_items(call_tool, workspace, update={arguments["id"]: arguments["item"]})
        item_id = arguments["id"]
    # 項目を消す
    elif name == "remove":
        write_items(call_tool, workspace, remove=[arguments["id"]])
        item_id = arguments["id"]
    # それ以外: ツールを呼ぶ
    else:
        return call_tool(name, **arguments)
    data = {"id": item_id}
    return ToolResult(is_error=False, text=json.dumps(data, ensure_ascii=False), data=data)


def call_or_write(call_tool: Callable[..., ToolResult], name: str, **arguments: Any) -> dict[str, Any]:
    """write_tool を呼び、エラーならテストを止めて結果の `data` を返す。"""
    result = write_tool(call_tool, name, **arguments)
    assert result.is_error is False, result.text
    assert result.data is not None
    return result.data


def _next_id(call_tool: Callable[..., ToolResult], workspace: str, kind: str) -> str:
    """`next_id` で種類の次の ID を 1 つ取る。"""
    result = call_tool("next_id", workspace=workspace, kind=kind)
    assert not result.is_error, result.text
    assert result.data is not None
    return str(result.data["ids"][0])


def _with_body(item: dict[str, Any], records: Path, texts: dict[Path, str | None]) -> dict[str, Any]:
    """本文の原文のキーを外して本文のファイルに書く分へ回し、`body` に本文のパスを入れた項目を返す。"""
    result = dict(item)
    for key, suffix in BODY_KEYS.items():
        text = result.pop(key, None)
        # 本文の原文を渡していない: 本文はそのまま
        if text is None:
            continue
        body = f"docs/{result['id']}{suffix}"
        result["body"] = body
        texts[records / body] = text
    return result


def _replace(path: Path, text: str | None) -> None:
    """一時ファイルに書いて置き換える（None はファイルを消す）。"""
    if text is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
