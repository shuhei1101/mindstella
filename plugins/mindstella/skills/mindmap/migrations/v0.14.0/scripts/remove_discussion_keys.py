"""設定と項目から議論のキーを消し、残す値をタグと本文へ移す（v0.14.0 の移し替え）。"""

from __future__ import annotations

import html as html_lib
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

# 記録のフォルダ（ワークスペースの直下からの相対パス）
RECORD_DIR = ".mindstella"

# 設定のファイル（記録のフォルダからの相対パス）
CONFIG_FILE = "config.yaml"

# 本文を置くフォルダ（記録のフォルダからの相対パス）
BODY_DIR = "docs"

# `.mindstella/config.yaml` から消すキー
REMOVED_SETTING_KEYS = ("goal", "phases", "playbooks", "targets", "target_label", "categories")

# 値を移さずに消す項目のキー
DROPPED_ITEM_KEYS = ("phase", "weight", "deliverable")

# タグへ移す項目のキー
TAG_KEYS = ("target", "category")

# 本文の表へ移す項目のキー
BODY_KEYS = ("attrs", "angles", "confidence")

# 書き換える種類ごとの YAML（記録のフォルダからの相対パス）
KIND_FILES = (
    "decisions.yaml",
    "tasks.yaml",
    "research.yaml",
    "docs.yaml",
    "terms.yaml",
    "notes.yaml",
    "logs.yaml",
)


def migrate(root: Path) -> list[str]:
    """設定と項目から削除するキーを消し、残す値をタグと本文へ移して、変えたファイルを返す。"""
    records = root / RECORD_DIR
    writes: dict[Path, str] = {}
    config_path = records / CONFIG_FILE
    config = _load(config_path)
    # 設定が削除するキーを持つ: 並びを保って消す
    if isinstance(config, dict) and any(key in config for key in REMOVED_SETTING_KEYS):
        kept = {key: value for key, value in config.items() if key not in REMOVED_SETTING_KEYS}
        writes[config_path] = _dump(kept)
    for file_name in KIND_FILES:
        path = records / file_name
        data = _load(path)
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            continue
        changed = False
        new_items: list[Any] = []
        for item in items:
            # 消すキーを持たない項目はそのまま
            if not isinstance(item, dict) or not _has_removed_key(item):
                new_items.append(item)
                continue
            new_items.append(_convert_item(item, records, writes))
            changed = True
        if changed:
            writes[path] = _dump({**data, "items": new_items})
    _replace_all(writes)
    return [path.relative_to(root).as_posix() for path in writes]


def _has_removed_key(item: dict[str, Any]) -> bool:
    """項目が消すキーを 1 つでも持つか。"""
    return any(key in item for key in (*TAG_KEYS, *BODY_KEYS, *DROPPED_ITEM_KEYS))


def _convert_item(item: dict[str, Any], records: Path, writes: dict[Path, str]) -> dict[str, Any]:
    """1 項目の対象・カテゴリーをタグへ、属性・観点・確かさを本文の表へ移し、消すキーを除いた項目を返す。"""
    converted = dict(item)
    tags = list(converted.get("tags") or [])
    names = {tag.get("name") for tag in tags if isinstance(tag, dict)}
    for key in TAG_KEYS:
        value = converted.get(key)
        name = f"topic:{value}"
        # 値があり、同じ名前のタグが無い: 末尾に足す
        if isinstance(value, str) and value and name not in names:
            tags.append({"name": name})
            names.add(name)
    if tags:
        converted["tags"] = tags
    sections = _body_sections(converted)
    if sections:
        body_name = converted.get("body")
        # 本文が無い: docs/{ID}.md を作って指す
        if not isinstance(body_name, str):
            body_name = f"{BODY_DIR}/{converted['id']}.md"
            converted["body"] = body_name
        body_path = records / body_name
        current = writes.get(body_path)
        if current is None:
            current = body_path.read_text(encoding="utf-8") if body_path.is_file() else ""
        writes[body_path] = _append_sections(current, sections, html=body_name.endswith(".html"))
    for key in (*TAG_KEYS, *BODY_KEYS, *DROPPED_ITEM_KEYS):
        converted.pop(key, None)
    return converted


def _body_sections(item: dict[str, Any]) -> list[tuple[str, list[tuple[str, str]]]]:
    """本文の末尾に足す見出しと表の行（属性・観点と確かさ）を返す。"""
    sections: list[tuple[str, list[tuple[str, str]]]] = []
    attrs = item.get("attrs")
    if isinstance(attrs, dict) and attrs:
        sections.append(("属性", [(str(key), str(value)) for key, value in attrs.items()]))
    rows: list[tuple[str, str]] = []
    angles = item.get("angles")
    if isinstance(angles, list) and angles:
        rows.append(("観点", "・".join(str(angle) for angle in angles)))
    confidence = item.get("confidence")
    if confidence is not None:
        rows.append(("確かさ", str(confidence)))
    if rows:
        sections.append(("観点と確かさ", rows))
    return sections


def _append_sections(
    text: str, sections: list[tuple[str, list[tuple[str, str]]]], *, html: bool
) -> str:
    """本文の末尾に、見出しと表を足した本文を返す。"""
    blocks: list[str] = []
    for heading, rows in sections:
        # HTML の本文: 見出しと table で足す
        if html:
            cells = "".join(
                f"<tr><td>{html_lib.escape(key)}</td><td>{html_lib.escape(value)}</td></tr>"
                for key, value in rows
            )
            blocks.append(f"<h2>{heading}</h2>\n<table><tbody>{cells}</tbody></table>")
        else:
            lines = [f"## {heading}", "", "| キー | 値 |", "| --- | --- |"]
            lines += [f"| {_markdown_cell(key)} | {_markdown_cell(value)} |" for key, value in rows]
            blocks.append("\n".join(lines))
    head = text.rstrip("\n")
    return (head + "\n\n" if head else "") + "\n\n".join(blocks) + "\n"


def _markdown_cell(text: str) -> str:
    """表のセルに入れる文字の `|` を打ち消し、改行を `<br>` にする。"""
    return text.replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")


def _load(path: Path) -> Any:
    """YAML を読む。無ければ None。"""
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RuntimeError(f"{path.name} を YAML として読めません") from error


def _dump(data: Any) -> str:
    """記録の YAML の書き方（日本語をそのまま・キーの並びを保つ）で文字列にする。"""
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def _replace_all(writes: dict[Path, str]) -> None:
    """全てのファイルを一時ファイルに書いてから置き換える。途中で失敗したら残った一時ファイルを消す。"""
    temps: list[tuple[Path, Path]] = []
    try:
        for path, text in writes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(text)
            temps.append((Path(temp), path))
        for temp, path in temps:
            os.replace(temp, path)
    finally:
        for temp, _ in temps:
            temp.unlink(missing_ok=True)
