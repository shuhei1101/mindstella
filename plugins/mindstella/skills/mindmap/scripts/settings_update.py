"""設定の更新（`update_settings`）の引数の確かめ・設定の置き換え・フェーズの付け替え・まとめた書き込み。"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from errors import ArgumentError, SchemaMismatchError, UnmappedPhaseError
from kinds import KINDS, SETTINGS_FILE
from store import (
    WHOLE_PATH,
    Change,
    NowFn,
    Workspace,
    build_mismatch_error,
    dump_yaml,
    load_workspace,
    loses_content_on_rewrite,
    now_utc,
    remove_files,
    validate_workspace,
    write_failed,
    write_temp,
)

# `update_settings` の `settings` に渡せるキー
EDITABLE_KEYS = ("summary", "description", "playbooks", "phases", "target_label", "goal")

# 値が `null` のときに消してよい任意のキー
REMOVABLE_KEYS = ("description", "goal")

# `phase_map` の引数の名前（引数の誤りに添える）
PHASE_MAP_ARGUMENT = "phase_map"


@dataclass(frozen=True, slots=True, kw_only=True)
class PhaseRemap:
    """フェーズを付け替えた 1 項目。"""

    # 項目の ID
    id: str
    # 前のフェーズ
    from_phase: str
    # 後のフェーズ
    to_phase: str


def validate_settings_input(
    settings: dict[str, Any], phase_map: dict[str, str] | None, current_phases: list[str]
) -> None:
    """`settings` のキーと `phase_map` の渡し方を、書き換える前に確かめる。"""
    lines = _settings_key_lines(settings)
    # 書き換えられないキー・消せないキーの null・空の settings
    if lines:
        raise SchemaMismatchError(lines)
    # phase_map を渡していない: 確かめることが無い
    if phase_map is None:
        return
    # phases を渡さずに phase_map だけを渡した
    if "phases" not in settings:
        raise ArgumentError(PHASE_MAP_ARGUMENT, "`settings` に `phases` を渡していません")
    new_phases = settings["phases"]
    for old_phase in phase_map:
        # 古いフェーズでないか、新しい phases にも残るフェーズ: 対応を渡せない
        if old_phase not in current_phases or old_phase in new_phases:
            raise ArgumentError(
                PHASE_MAP_ARGUMENT,
                f"{old_phase} は、今の `phases` にあって新しい `phases` に無いフェーズではありません",
            )
    # 対応の値が新しい phases に無い
    unmapped = [(old, new) for old, new in phase_map.items() if new not in new_phases]
    if unmapped:
        raise UnmappedPhaseError(unmapped)


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
        # 前と値が違う（無かったキーを含む）ものだけを変わったキーにする
        if key not in merged or merged[key] != value:
            changed.append(key)
        merged[key] = value
    return merged, changed


def remap_phases(
    workspace: Workspace,
    settings: dict[str, Any],
    phase_map: dict[str, str],
    now: NowFn = now_utc,
) -> tuple[list[Change], list[PhaseRemap], dict[str, Any]]:
    """新しい phases に無いフェーズを持つ項目と goal.phase を、対応で付け替える。"""
    phases = settings.get("phases", [])
    changes: list[Change] = []
    remapped: list[PhaseRemap] = []
    unmapped: list[tuple[str, str]] = []
    for kind in KINDS:
        items = [dict(item) for item in workspace.items[kind]]
        remapped_here = False
        for item in items:
            phase = item.get("phase")
            # フェーズを持たないか、新しい phases にある項目は触らない
            if not isinstance(phase, str) or phase in phases:
                continue
            # 対応が無い: 残るものとして控える
            if phase not in phase_map:
                unmapped.append((str(item.get("id")), phase))
                continue
            # 対応がある: フェーズと更新日時を置き換える
            item["phase"] = phase_map[phase]
            item["updated"] = now()
            remapped.append(
                PhaseRemap(id=item["id"], from_phase=phase, to_phase=phase_map[phase])
            )
            remapped_here = True
        # 付け替えた項目がある種類だけ、並び全体を変更にする
        if remapped_here:
            changes.append(Change(kind=kind, items=items))
    new_settings = dict(settings)
    goal = new_settings.get("goal")
    if isinstance(goal, dict) and goal.get("phase") not in phases:
        goal_phase = goal.get("phase")
        if goal_phase in phase_map:
            # ゴールのフェーズにも対応がある: 置き換える
            new_settings["goal"] = {**goal, "phase": phase_map[goal_phase]}
        else:
            # 対応が無い: 残るものとして控える
            unmapped.append(("goal", str(goal_phase)))
    if unmapped:
        raise UnmappedPhaseError(unmapped)
    return changes, remapped, new_settings


def save_settings(
    workspace: Workspace, settings: dict[str, Any], changes: list[Change]
) -> list[str]:
    """設定と、フェーズを付け替えた種類の項目の並びを、検証してから全て書き換えるか、どれも書き換えない。"""
    # 書き戻すと中身を失う形のファイルには書かない
    for change in changes:
        if loses_content_on_rewrite(workspace, change.kind):
            file_name = KINDS[change.kind].file
            current = [p for p in validate_workspace(workspace) if p.file == file_name]
            raise build_mismatch_error(current, workspace)
    # 書き換えた後のワークスペース全体を検証する
    raw = {
        **workspace.raw,
        SETTINGS_FILE: settings,
        **{KINDS[change.kind].file: {"items": change.items} for change in changes},
    }
    changed = replace(workspace, raw=raw)
    problems = validate_workspace(changed)
    if problems:
        raise build_mismatch_error(problems, changed)

    # 置き換える順（種類のファイル → 設定）に、書く先と中身を並べる
    targets = [(KINDS[change.kind].file, {"items": change.items}) for change in changes]
    targets.append((SETTINGS_FILE, settings))
    # 一時ファイルを先に全て書き、置き換える前の中身を控える
    temps: list[tuple[Path, Path]] = []
    previous: dict[Path, bytes] = {}
    for file_name, data in targets:
        path = workspace.root / file_name
        try:
            previous[path] = path.read_bytes()
            temps.append((write_temp(path, dump_yaml(data)), path))
        except OSError as error:
            remove_files([temp for temp, _ in temps])
            raise write_failed(path, error) from error
    # 順に置き換え、失敗したら置き換えたファイルを控えに戻す
    replaced: list[Path] = []
    for temp, path in temps:
        try:
            os.replace(temp, path)
        except OSError as error:
            for done in replaced:
                done.write_bytes(previous[done])
            remove_files([leftover for leftover, _ in temps])
            raise write_failed(path, error) from error
        replaced.append(path)
    # mindmap.yaml を先頭にして返す
    return [SETTINGS_FILE, *(KINDS[change.kind].file for change in changes)]


def update_settings(
    root: Path,
    settings: dict[str, Any],
    phase_map: dict[str, str] | None,
    now: NowFn = now_utc,
) -> dict[str, Any]:
    """引数を確かめ、設定を置き換えてフェーズを付け替え、まとめて書く。"""
    workspace = load_workspace(root)
    current_phases = workspace.settings.get("phases", [])
    validate_settings_input(settings, phase_map, current_phases)
    merged, changed = merge_settings(workspace.settings, settings)
    # 書き換えのたびに確かめるので、phases に無いフェーズが残れば止まる
    changes, remapped, remapped_settings = remap_phases(
        workspace, merged, phase_map or {}, now
    )
    # 対応で goal.phase だけが変わったときも goal を変わったキーに入れる
    if remapped_settings.get("goal") != merged.get("goal") and "goal" not in changed:
        changed.append("goal")
    files = save_settings(workspace, remapped_settings, changes)
    return {
        "changed": changed,
        "remapped": [
            {"id": item.id, "from": item.from_phase, "to": item.to_phase} for item in remapped
        ],
        "files": files,
    }


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
    return lines
