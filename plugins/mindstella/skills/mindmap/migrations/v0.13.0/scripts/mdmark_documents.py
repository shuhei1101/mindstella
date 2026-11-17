"""資料の Markdown を mdmark の今の書き方（JSON のマーカー・map の図）へ移す（v0.13.0 の移し替え）。"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml
from kinds import RECORD_DIR, SETTINGS_FILE
from store import dump_yaml, remove_files, write_temp

# `npx` に渡す mdmark の取得元の書式（`{ref}` にタグか `develop`）
MDMARK_REPO_SPEC = "github:shuhei1101/mdmark#{ref}"

# 一時の mdmark の設定の `version`。ここから `v0.11.0`（マーカーの JSON）と `v0.13.0`（map）の手順が当たる
MDMARK_BASE_VERSION = "v0.10.0"

# 設定されていれば `npx -y {取得元}` の代わりに呼ぶコマンド（空白区切り）
MDMARK_COMMAND_ENV = "MINDSTELLA_MDMARK_COMMAND"

# 一時の mdmark の設定のファイル名と、mdmark が写しを置くフォルダ名（どちらも `.mindstella/` の下）
TEMP_CONFIG = "mdmark.config.yaml"
MDMARK_WORK_DIR = ".mdmark"

# 設定の mdmark のバージョンの既定と、`latest` が指す mdmark のブランチ
LATEST = "latest"
LATEST_REF = "develop"

# 一時の設定が対象にする資料の Markdown と、mdmark の点検が求める書き出し先（どちらも `.mindstella/` からの相対。書き出し先は終わりに消す `.mdmark/` の下）
DOCS_GLOB = "docs/**/*.md"
BUILD_OUT = f"{MDMARK_WORK_DIR}/site.html"

# 標準出力のうち、移行の報告の行の頭
REPORT_PREFIX = "  docs/"


def migrate(root: Path) -> tuple[list[str], list[str]]:
    """mdmark の `upgrade` で資料を移し、書き足された map の種類を config.yaml へ移す。変えたファイルと報告の行を返す。"""
    record = root / RECORD_DIR
    config_path = record / SETTINGS_FILE
    settings = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    before = _snapshot(record)
    temp_config = record / TEMP_CONFIG
    temp_config.write_text(
        dump_yaml({"version": MDMARK_BASE_VERSION, "build": {"include": [DOCS_GLOB], "out": BUILD_OUT}}),
        encoding="utf-8",
    )
    try:
        result = _run_upgrade(record, temp_config, _mdmark_ref(settings))
        if result.returncode != 0:
            raise RuntimeError(f"mdmark の変換が失敗しました: {result.stdout}{result.stderr}")
        mdmark_map = (yaml.safe_load(temp_config.read_text(encoding="utf-8")) or {}).get("map")
    finally:
        _remove_temp(record)
    changed = [f"{RECORD_DIR}/{name}" for name, body in _snapshot(record).items() if before.get(name) != body]
    if mdmark_map:
        _write_map(config_path, settings, mdmark_map)
        changed.append(f"{RECORD_DIR}/{SETTINGS_FILE}")
    report = [line for line in result.stdout.splitlines() if line.startswith(REPORT_PREFIX)]
    return changed, report


def _mdmark_ref(settings: dict[str, Any]) -> str:
    """設定の `mdmark.version`（無ければ `latest`）から、取得元の ref を決める。"""
    mdmark = settings.get("mdmark")
    version = mdmark.get("version") if isinstance(mdmark, dict) else None
    return LATEST_REF if version in (None, LATEST) else str(version)


def _run_upgrade(record: Path, temp_config: Path, ref: str) -> subprocess.CompletedProcess[str]:
    """mdmark の CLI の `upgrade --yes` を、記録のフォルダを作業場所にして呼ぶ。"""
    override = os.environ.get(MDMARK_COMMAND_ENV)
    command = shlex.split(override) if override else ["npx", "-y", MDMARK_REPO_SPEC.format(ref=ref)]
    try:
        return subprocess.run(
            [*command, "upgrade", "--yes", "--config", str(temp_config)],
            cwd=record,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise RuntimeError(f"mdmark の変換が失敗しました: {error}") from error


def _snapshot(record: Path) -> dict[str, bytes]:
    """資料の Markdown の中身を、記録のフォルダからの相対パスごとに読む。"""
    return {
        path.relative_to(record).as_posix(): path.read_bytes()
        for path in sorted((record / "docs").rglob("*.md"))
        if path.is_file()
    }


def _remove_temp(record: Path) -> None:
    """一時の mdmark の設定と mdmark の写しを消す。"""
    (record / TEMP_CONFIG).unlink(missing_ok=True)
    shutil.rmtree(record / MDMARK_WORK_DIR, ignore_errors=True)


def _write_map(config_path: Path, settings: dict[str, Any], mdmark_map: Any) -> None:
    """config.yaml の `mdmark.map` に map を入れ（`version` はそのまま）、キーの並びを保って書き換える。"""
    current = settings.get("mdmark")
    settings["mdmark"] = {**(current if isinstance(current, dict) else {}), "map": mdmark_map}
    temp = write_temp(config_path, dump_yaml(settings))
    try:
        os.replace(temp, config_path)
    except OSError:
        remove_files([temp])
        raise
