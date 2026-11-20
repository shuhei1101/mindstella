"""設定の更新（`update_settings`）の引数の確かめ・設定の置き換え・設定の書き込み。"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from errors import ArgumentError, SchemaMismatchError, SettingsInvalidError
from kinds import RECORD_DIR, SETTINGS_FILE, records_root
from store import (
    WHOLE_PATH,
    Workspace,
    build_mismatch_error,
    check_settings,
    dump_yaml,
    format_path,
    load_display_validator,
    load_workspace,
    remove_files,
    validate_workspace,
    write_failed,
    write_temp,
)

# `update_settings` の `settings` に渡せるキー
EDITABLE_KEYS = (
    "summary",
    "description",
    "links",
    "history_limit",
    "display",
    "transcription",
    "mdmark",
    "confirm_on_comment",
)

# 値が `null` のときに消してよい任意のキー
REMOVABLE_KEYS = ("description", "links", "history_limit", "display", "transcription", "confirm_on_comment")

# 渡すと引数の誤りにする、削除した設定のキー
REMOVED_KEYS = ("goal", "phases", "playbooks", "targets", "target_label", "categories")

# mdmark の設定のキーと、そのうち `update_settings` で書き換えられるキー
MDMARK_KEY = "mdmark"
MDMARK_EDITABLE_KEYS = ("version",)

# 表示の既定の書き換えの本文に必須のキー（これ以外のキーは受け付けない）
DISPLAY_KEYS = ("visible_kinds",)


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsStage:
    """書き込む前にメモリの上で当てた設定。"""

    # 当てた後の設定
    settings: dict[str, Any]
    # 変わった設定のキー
    changed: list[str]


def validate_settings_input(settings: dict[str, Any]) -> None:
    """`settings` のキーを、書き換える前に確かめる。"""
    removed = [key for key in settings if key in REMOVED_KEYS]
    # 削除したキーを渡した
    if removed:
        raise ArgumentError("settings", f"削除したキーです: {'・'.join(removed)}")
    lines = _settings_key_lines(settings)
    # 書き換えられないキー・消せないキーの null・空の settings
    if lines:
        raise SchemaMismatchError(lines)


def merge_settings(
    current: dict[str, Any], settings: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """今の設定に渡したキーを当て、置き換えた設定と、値が変わった・消えたキーの名前を返す。"""
    # キーの並びを保つため、今の設定の写しに当てる
    merged = dict(current)
    changed: list[str] = []
    for key, value in settings.items():
        # null: キーを消す（元から無ければ変わらない）
        if value is None:
            if key in merged:
                del merged[key]
                changed.append(key)
            continue
        # mdmark: version だけを置き換え、移し替えが書いた map を残す
        if key == MDMARK_KEY and isinstance(merged.get(key), dict):
            value = {**merged[key], **value}
        # 前と値が違う（無かったキーを含む）ものだけを変わったキーにする
        if key not in merged or merged[key] != value:
            changed.append(key)
        merged[key] = value
    return merged, changed


def save_settings(workspace: Workspace, settings: dict[str, Any]) -> list[str]:
    """設定を検証してから `config.yaml` を置き換える。変わらなければ書かずに空を返す。"""
    # 設定が変わらない: 書かない
    if settings == workspace.settings:
        return []
    # 差し替えた後のワークスペース全体を検証する
    changed = replace(workspace, raw={**workspace.raw, SETTINGS_FILE: settings})
    problems = validate_workspace(changed)
    if problems:
        raise build_mismatch_error(problems, changed)
    path = records_root(workspace.root) / SETTINGS_FILE
    try:
        temp = write_temp(path, dump_yaml(settings))
    except OSError as error:
        raise write_failed(path, error) from error
    try:
        os.replace(temp, path)
    except OSError as error:
        # 置き換えられなかった一時ファイルは残さない
        remove_files([temp])
        raise write_failed(path, error) from error
    return [f"{RECORD_DIR}/{SETTINGS_FILE}"]


def stage_settings(workspace: Workspace, settings: dict[str, Any]) -> SettingsStage:
    """引数を確かめ、設定を置き換え、書かずに結果を返す。"""
    validate_settings_input(settings)
    merged, changed = merge_settings(workspace.settings, settings)
    return SettingsStage(settings=merged, changed=changed)


def update_settings(root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    """引数を確かめ、設定を置き換えて書く。"""
    workspace = load_workspace(root)
    staged = stage_settings(workspace, settings)
    files = save_settings(workspace, staged.settings)
    return {"changed": staged.changed, "files": files}


def update_display(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """要求の本文の `visible_kinds` で `config.yaml` の `display` だけを丸ごと置き換える。"""
    # 本文に必須のキーがあるか
    for key in DISPLAY_KEYS:
        if key not in body:
            raise SettingsInvalidError(f"{key}: 渡してください")
    # 決めたキーのほか（削除した network_look を含む）は受け付けない
    unknown = [key for key in body if key not in DISPLAY_KEYS]
    if unknown:
        raise SettingsInvalidError("、".join(f"{key}: 知らないキーです" for key in unknown))
    # 本文の値を、設定のスキーマの display と突き合わせる
    display = {key: body[key] for key in DISPLAY_KEYS}
    found = sorted(
        load_display_validator().iter_errors(display), key=lambda error: list(error.absolute_path)
    )
    if found:
        raise SettingsInvalidError(
            "、".join(f"{format_path(error.absolute_path)}: {error.message}" for error in found)
        )
    # 崩れた config.yaml の上には書き足さない
    _, problems = check_settings(root)
    if problems:
        raise build_mismatch_error(problems)
    # 読んだ設定の display を置き換える（キーの並びは保ち、無ければ末尾に足す）
    workspace = load_workspace(root)
    settings = {**workspace.settings, "display": display}
    # 変更履歴にも書き換えのまとまりにも入れず、設定だけを書く
    save_settings(workspace, settings)
    return {"display": display}


def _settings_key_lines(settings: dict[str, Any]) -> list[str]:
    """`settings` が空か、書き換えられないキー・消せないキーの null を持つときの、問題ごとの行を返す。"""
    # 何も渡していない
    if not settings:
        return [f"{SETTINGS_FILE}: {WHOLE_PATH}: 1 つ以上のキーを渡してください"]
    lines: list[str] = []
    for key, value in settings.items():
        # 書き換えられないキー
        if key not in EDITABLE_KEYS:
            lines.append(f"{SETTINGS_FILE}: {key}: このツールでは書き換えられません")
        # 必須のキーを null で消そうとした
        elif value is None and key not in REMOVABLE_KEYS:
            lines.append(f"{SETTINGS_FILE}: {key}: null で消せません")
        # mdmark は version だけを書き換えられる（map は移し替えの手順だけが書く）
        elif key == MDMARK_KEY and isinstance(value, dict):
            lines.extend(
                f"{SETTINGS_FILE}: {MDMARK_KEY}.{name}: 書き換えられないキー"
                for name in value
                if name not in MDMARK_EDITABLE_KEYS
            )
    return lines
