"""ワークスペースの YAML と本文の読み込み・検証・採番・書き込み。"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import tempfile
import threading
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, Literal

import yaml
from errors import (
    ItemNotFoundError,
    SchemaMismatchError,
    WorkspaceExistsError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from jsonschema import Draft202012Validator
from kinds import (
    BODY_DIR,
    KINDS,
    LEGACY_SETTINGS_FILE,
    RECORD_DIR,
    RELEASE_DIR,
    SETTINGS_FILE,
    Kind,
    kind_of_id,
    records_root,
)
from readme import README_FILE, write_readme
from referencing import Registry
from referencing.jsonschema import DRAFT202012

# このファイルから見た `skills/mindmap/schemas/`
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

# Registry に登録し、各種類のスキーマが `$ref` で指す共通のスキーマの名前
COMMON_SCHEMA = "common.schema.json"

# `config.yaml` を検証するスキーマ
SETTINGS_SCHEMA = "settings.schema.json"

# 置き換える前に書く一時ファイルの拡張子（置き換えるファイルと同じフォルダに作る）
TEMP_SUFFIX = ".tmp"

# 置き換え先が無いときの一時ファイルの権限（umask で削る前の値）
DEFAULT_FILE_MODE = 0o666

# 一番上など、キーのパスが空のときの表記
WHOLE_PATH = "(全体)"

# 前の版の形式でスキーマに合わないときに、エラーの最後に続ける 1 行
LEGACY_HINT = "ヒント: 前の版の形式の記録は /mindstella:upgrade で今の形式に移せます"

# 記録のフォルダが無く直下に前の版の設定ファイルがあるフォルダの WorkspaceNotFoundError・WorkspaceExistsError に続ける 1 行（`{root}` はフォルダの絶対パス）
UPGRADE_HINT = (
    "ヒント: 前の版の形の記録があります。/mindstella:upgrade {root} で今の版へ移し替えてください"
)

# ワークスペースを最後に整えたときのプラグインの版を持つファイルの名前（`records_root` の下。v0.6.0 より前は直下）
VERSION_FILE = "mindstella-version.ini"

# プロセスをまたいだ書き換えの排他に使う空のファイルの名前（`records_root` の下）
LOCK_FILE = ".mindstella.lock"

# 書き換えのまとまりを持つファイルの名前（`records_root` の下）
CHANGES_FILE = "changes.yaml"

# 案（`options`）を持たなくてよい検討事項の状態
OPTIONS_OPTIONAL_STATUSES = frozenset({"未整理", "対象外", "取り下げ"})

# 今の日時（UTC のタイムゾーン付き ISO 8601）を返す関数。テストで決めた日時を注入する
type NowFn = Callable[[], str]


@dataclass(frozen=True, slots=True, kw_only=True)
class Problem:
    """スキーマ違反・参照切れなど 1 件の問題。"""

    kind: Literal[
        "schema",
        "duplicate_id",
        "broken_ref",
        "missing_body",
        "orphan_body",
        "unknown_phase",
        "stale_history",
        "decision_state",
    ]
    # ワークスペースからの相対パス
    file: str
    # 問題のある項目の ID
    id: str | None
    # `items[0].status` の形のキーのパス
    key: str | None
    # 中身（参照先の ID・スキーマの理由など）
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Workspace:
    """読み込んだ設定・種類ごとの項目・読めなかったファイル。"""

    # ワークスペースのフォルダ（絶対パス）
    root: Path
    # ファイル名 → 読んだ値そのまま。YAML として読めないファイルは含めない
    raw: dict[str, Any]
    # `config.yaml` の値。辞書でない・読めないときは空
    settings: dict[str, Any]
    # 種類ごとの `items`（ファイルの並びのまま）。形が合わないときは空
    items: dict[Kind, list[dict[str, Any]]]
    # YAML として読めなかったファイル
    load_problems: list[Problem]


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemRef:
    """ID で引いた項目と、その種類・並びの位置。"""

    kind: Kind
    # `items` の中の位置
    index: int
    item: dict[str, Any]


@dataclass(frozen=True, slots=True, kw_only=True)
class BodyWrite:
    """`docs/` に書く 1 つの本文。"""

    # `docs/` の中のファイル名（`{ID}.md`）
    name: str
    # 本文の Markdown
    text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Change:
    """1 つの種類の項目の並びを丸ごと置き換える変更と、一緒に書く本文。"""

    kind: Kind
    # 書き換えた後の `items` の並び全体
    items: list[dict[str, Any]]
    body: BodyWrite | None = None
    # 一緒に書く `changes.yaml` の新しい中身。変えないときは None
    changes: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class BatchChange:
    """複数の種類の項目の並びと複数の本文とまとまりを、一緒に書く変更。"""

    # 書き換える種類 → 書き換えた後の `items` の並び全体（書き換えない種類は持たない）
    items: dict[Kind, list[dict[str, Any]]]
    # 一緒に書く本文（同じ名前は 1 つだけ。後のものを残す）
    bodies: list[BodyWrite] = field(default_factory=list)
    # 一緒に書く `changes.yaml` の新しい中身。変えないときは None
    changes: dict[str, Any] | None = None


def load_workspace(root: Path) -> Workspace:
    """設定と 7 種類の YAML を読む。読めないファイルは問題に記録して空として扱う。"""
    root = root.resolve()
    # .mindstella/config.yaml が無いフォルダはワークスペースではない
    require_workspace(root)

    records = records_root(root)
    raw: dict[str, Any] = {}
    load_problems: list[Problem] = []
    for file_name in [SETTINGS_FILE, *(spec.file for spec in KINDS.values())]:
        path = records / file_name
        # 種類のファイルが無い: 項目が 0 件のものとして扱う
        if not path.is_file():
            raw[file_name] = {"items": []}
            continue
        try:
            raw[file_name] = _read_yaml(path)
        except yaml.YAMLError as error:
            # YAML として読めない: 問題に記録し、raw には入れない
            load_problems.append(
                Problem(
                    kind="schema",
                    file=file_name,
                    id=None,
                    key=WHOLE_PATH,
                    detail=f"YAML として読めません: {' '.join(str(error).split())}",
                )
            )

    settings = raw.get(SETTINGS_FILE)
    return Workspace(
        root=root,
        raw=raw,
        settings=settings if isinstance(settings, dict) else {},
        items={kind: _extract_items(raw.get(spec.file)) for kind, spec in KINDS.items()},
        load_problems=load_problems,
    )


def require_workspace(root: Path) -> None:
    """`.mindstella/config.yaml` があるかを確かめ、無ければ送る。直下に前の版の設定ファイルだけがあれば移し替えを案内する。"""
    # .mindstella/config.yaml がある: ワークスペース
    if (records_root(root) / SETTINGS_FILE).is_file():
        return
    # 直下に前の版の設定ファイルだけがある: 移し替えの案内を添える
    if (root / SETTINGS_FILE).is_file() or (root / LEGACY_SETTINGS_FILE).is_file():
        raise WorkspaceNotFoundError(
            f"ワークスペースがありません: {root}",
            [UPGRADE_HINT.replace("{root}", str(root))],
        )
    # どれも無い
    raise WorkspaceNotFoundError(f"ワークスペースがありません: {root}")


def check_settings(root: Path) -> tuple[dict[str, Any], list[Problem]]:
    """`config.yaml` だけを読んで設定のスキーマと突き合わせ、読んだ設定と問題を返す。"""
    root = root.resolve()
    require_workspace(root)
    try:
        value = _read_yaml(records_root(root) / SETTINGS_FILE)
    except yaml.YAMLError as error:
        # YAML として読めない: 空の設定と、全体の問題 1 件を返す
        problem = Problem(
            kind="schema",
            file=SETTINGS_FILE,
            id=None,
            key=WHOLE_PATH,
            detail=f"YAML として読めません: {' '.join(str(error).split())}",
        )
        return {}, [problem]
    # スキーマと突き合わせ、キーのパスの順に問題を並べる
    validator = load_validators()[SETTINGS_SCHEMA]
    found = sorted(
        validator.iter_errors(value), key=lambda error: _path_order(list(error.absolute_path))
    )
    problems = [
        Problem(
            kind="schema",
            file=SETTINGS_FILE,
            id=None,
            key=_format_path(list(error.absolute_path)),
            detail=error.message,
        )
        for error in found
    ]
    return (value if isinstance(value, dict) else {}), problems


def _open_lock_file(lock_dir: Path) -> IO[str]:
    """ロックのファイルを追記で開く。開けなければ書き込めなかったエラーにする。"""
    lock_path = lock_dir / LOCK_FILE
    try:
        return lock_path.open("a")
    except OSError as error:
        raise write_failed(lock_path, error) from error


@contextlib.contextmanager
def workspace_lock(
    root: Path,
    process_lock: threading.Lock,
    *,
    create: bool = False,
    require: Callable[[Path], None] = require_workspace,
) -> Iterator[None]:
    """プロセスの中の鍵とワークスペースの排他ロックをこの順に取り、抜けるときに放す。"""
    records = records_root(root)
    with process_lock:
        root_created = records_created = False
        if create:
            # まだ無いフォルダへ書く `init` のために、記録のフォルダごと作る
            root_created = not root.exists()
            records_created = not records.exists()
            records.mkdir(parents=True, exist_ok=True)
        else:
            # ワークスペースでないフォルダには何も作らず止める
            require(root)
        # 記録のフォルダが無い（移す前の形）ときだけ、直下にロックのファイルを置く
        lock_dir = records if records.is_dir() else root
        try:
            with _open_lock_file(lock_dir) as stream:
                # 別のプロセスが持っている間は、取れるまで待つ
                fcntl.flock(stream, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(stream, fcntl.LOCK_UN)
        except BaseException:
            # この鍵で作った記録のフォルダに、ロックのファイルしか無いまま失敗したときは、何も作らなかった形に戻す
            if records_created and [path.name for path in records.iterdir()] == [LOCK_FILE]:
                (records / LOCK_FILE).unlink()
                records.rmdir()
                # 無かった root も、空になったら消す
                if root_created and not any(root.iterdir()):
                    root.rmdir()
            raise


def validate_workspace(workspace: Workspace) -> list[Problem]:
    """設定と 7 種類をスキーマと突き合わせ、合わない箇所を問題の並びにする。"""
    validators = load_validators()
    # ファイル名の順・同じファイルの中はキーのパスの順に並べるための (ファイル名, パスの順, 問題)
    entries: list[tuple[str, tuple[tuple[int, Any], ...], Problem]] = [
        (problem.file, (), problem) for problem in workspace.load_problems
    ]
    schema_by_file = {SETTINGS_FILE: SETTINGS_SCHEMA}
    schema_by_file.update({spec.file: spec.schema for spec in KINDS.values()})
    for file_name, schema_name in schema_by_file.items():
        # 読めなかったファイルは load_problems が持っているので突き合わせない
        if file_name not in workspace.raw:
            continue
        value = workspace.raw[file_name]
        for error in validators[schema_name].iter_errors(value):
            path = list(error.absolute_path)
            problem = Problem(
                kind="schema",
                file=file_name,
                id=_item_id_at(value, path),
                key=_format_path(path),
                detail=error.message,
            )
            entries.append((file_name, _path_order(path), problem))
    # 検討事項の案と状態の決まりは、スキーマでは見られないのでここで足す
    decisions_file = KINDS["decision"].file
    if decisions_file in workspace.raw:
        for index, name, problem in _decision_rule_hits(workspace.raw[decisions_file]):
            entries.append((decisions_file, _path_order(["items", index, name]), problem))
    entries.sort(key=lambda entry: (entry[0], entry[1]))
    return [problem for _, _, problem in entries]


def check_decision_rules(decisions: Any) -> list[Problem]:
    """検討事項の並びを案と状態の決まりと突き合わせ、合わない決まりごとに問題にする。"""
    return [problem for _, _, problem in _decision_rule_hits(decisions)]


def _decision_rule_hits(decisions: Any) -> list[tuple[int, str, Problem]]:
    """案と状態の決まりに合わない問題を、項目の位置・問題のキー（`options` か `status`）つきで返す。"""
    # 一番上が辞書で `items` が配列のときだけ見る（形の誤りはスキーマの検証が拾う）
    if not isinstance(decisions, dict) or not isinstance(decisions.get("items"), list):
        return []
    problems: list[tuple[int, str, Problem]] = []
    for index, item in enumerate(decisions["items"]):
        # 辞書でない要素と、状態・案の型がスキーマに合わない要素は、スキーマの検証が拾う
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        options = item.get("options", [])
        if not isinstance(status, str) or not isinstance(options, list):
            continue
        item_id = item.get("id") if isinstance(item.get("id"), str) else None
        label = item_id or f"items[{index}]"
        adopted = [
            option
            for option in options
            if isinstance(option, dict) and option.get("adopted") is True
        ]
        # 案を持たなくてよい状態以外は、案を 1 つ以上持つ
        if status not in OPTIONS_OPTIONAL_STATUSES and not options:
            problems.append(
                (
                    index,
                    "options",
                    _decision_problem(
                        item_id,
                        f"items[{index}].options",
                        f"{label} は状態 {status} のため案を 1 つ以上持つ（options に案を書く）",
                    ),
                )
            )
        # 決定済みは、採用した案を持つ
        if status == "決定済み" and not adopted:
            problems.append(
                (
                    index,
                    "options",
                    _decision_problem(
                        item_id,
                        f"items[{index}].options",
                        f"{label} は決定済みなのに採用した案を持たない（adopt で案を採用する）",
                    ),
                )
            )
        # 採用した案を持つ検討事項は、未決定にしない
        if status == "未決定" and adopted:
            problems.append(
                (
                    index,
                    "status",
                    _decision_problem(
                        item_id,
                        f"items[{index}].status",
                        f"{label} は採用した案 {adopted[0].get('key')} を持つのに未決定"
                        "（adopt で決定済みにするか、採用を外す）",
                    ),
                )
            )
    return problems


def _decision_problem(item_id: str | None, key: str, detail: str) -> Problem:
    """案と状態の決まりに合わない問題 1 件を作る。"""
    return Problem(
        kind="decision_state", file=KINDS["decision"].file, id=item_id, key=key, detail=detail
    )


def _load_registry() -> Registry:
    """共通のスキーマを登録した Registry を返す（各種類のスキーマが `common.schema.json#/$defs/...` で指せるように）。"""
    common = json.loads((SCHEMA_DIR / COMMON_SCHEMA).read_text(encoding="utf-8"))
    return Registry().with_resources([(COMMON_SCHEMA, DRAFT202012.create_resource(common))])


def load_display_validator() -> Draft202012Validator:
    """設定のスキーマの `display` の部分だけを検証する検証器を作る（選べる見た目と種類の名前はスキーマだけが持つ）。"""
    schema = json.loads((SCHEMA_DIR / SETTINGS_SCHEMA).read_text(encoding="utf-8"))
    return Draft202012Validator(schema["properties"]["display"], registry=_load_registry())


def load_validators() -> dict[str, Draft202012Validator]:
    """共通のスキーマを Registry に登録し、設定と 7 種類の検証器を作る。"""
    registry = _load_registry()
    schema_names = [SETTINGS_SCHEMA, *(spec.schema for spec in KINDS.values())]
    validators: dict[str, Draft202012Validator] = {}
    for schema_name in schema_names:
        schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
        validators[schema_name] = Draft202012Validator(schema, registry=registry)
    return validators


def find_item(workspace: Workspace, item_id: str) -> ItemRef:
    """ID で項目を引く。"""
    kind = kind_of_id(item_id)
    # 形が合わないか、頭の文字がどの種類にも当たらない
    if kind is None:
        raise ItemNotFoundError(f"項目がありません: {item_id}")
    for index, item in enumerate(workspace.items[kind]):
        if item.get("id") == item_id:
            return ItemRef(kind=kind, index=index, item=item)
    # その種類に ID の項目が無い
    raise ItemNotFoundError(f"項目がありません: {item_id}")


def next_id(workspace: Workspace, kind: Kind) -> str:
    """その種類の連番の最大 + 1 の ID を返す。"""
    numbers = [
        int(item_id.split("-", 1)[1])
        for item_id in (item.get("id") for item in workspace.items[kind])
        if isinstance(item_id, str) and kind_of_id(item_id) == kind
    ]
    return f"{KINDS[kind].prefix}-{max(numbers, default=0) + 1}"


def now_utc() -> str:
    """今の日時を UTC のタイムゾーン付き ISO 8601（秒まで）で返す。"""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def build_mismatch_error(
    problems: list[Problem],
    workspace: Workspace | None = None,
    *,
    written_ids: frozenset[str] = frozenset(),
) -> SchemaMismatchError:
    """問題ごとの `{ファイル名}: {キーのパス}: {理由}` の行を持つ例外を作る。workspace を渡すと前の版の形式の問題かも決める。"""
    lines = [
        f"{problem.file}: {problem.key or WHOLE_PATH}: {problem.detail}" for problem in problems
    ]
    legacy = workspace is not None and any(
        is_legacy_problem(p, workspace, written_ids=written_ids) for p in problems
    )
    return SchemaMismatchError(lines, legacy=legacy)


def is_legacy_problem(
    problem: Problem, workspace: Workspace, *, written_ids: frozenset[str] = frozenset()
) -> bool:
    """問題が、前の版の形式（資料の `done`・題名の無い設定・`field` を持つ設定・書き込む項目以外の案と状態の合わない検討事項）から来ているかを返す。"""
    # 案と状態の合わない検討事項は、書き込む項目のものでなければ前の版の形式から来ている
    if problem.kind == "decision_state":
        return problem.id not in written_ids
    # スキーマ違反以外（参照切れなど）は前の版の形式のせいではない
    if problem.kind != "schema":
        return False
    # 設定: 題名（summary）が無いか、field を持ち playbooks を持たない
    if problem.file == SETTINGS_FILE:
        raw_settings = workspace.raw.get(SETTINGS_FILE)
        return isinstance(raw_settings, dict) and (
            "summary" not in raw_settings
            or ("field" in raw_settings and "playbooks" not in raw_settings)
        )
    # 資料: done を持ち、status を持たない
    if problem.file == KINDS["doc"].file and problem.id is not None:
        docs = _extract_items(workspace.raw.get(problem.file))
        return any(
            item.get("id") == problem.id and "done" in item and "status" not in item
            for item in docs
        )
    return False


def save_change(workspace: Workspace, change: Change) -> None:
    """1 種類の項目の並びと本文とまとまりを、検証してから全て書き換えるか、どれも書き換えない。"""
    spec = KINDS[change.kind]
    # 書き戻すと中身を失う形のファイルには書かない（変更を当てる前の、そのファイルの問題を返す）
    if _loses_content_on_rewrite(workspace, change.kind):
        current = [p for p in validate_workspace(workspace) if p.file == spec.file]
        raise build_mismatch_error(current, workspace)
    # 変更を当てた後のワークスペース全体を検証する
    changed_raw = {**workspace.raw, spec.file: {"items": change.items}}
    changed = replace(workspace, raw=changed_raw)
    problems = validate_workspace(changed)
    if problems:
        written_ids = _written_ids(workspace.items[change.kind], change.items)
        raise build_mismatch_error(problems, changed, written_ids=written_ids)

    records = records_root(workspace.root)
    yaml_path = records / spec.file
    changes_path = records / CHANGES_FILE
    body_path = records / BODY_DIR / change.body.name if change.body else None
    # 置き換える前の中身を控える（無ければ None）
    previous_body = body_path.read_bytes() if body_path and body_path.is_file() else None
    previous_yaml = yaml_path.read_bytes() if yaml_path.is_file() else None

    # 一時ファイルを先に全て書く
    temps: list[Path] = []
    body_temp: Path | None = None
    changes_temp: Path | None = None
    try:
        yaml_temp = write_temp(yaml_path, dump_yaml({"items": change.items}))
        temps.append(yaml_temp)
        if change.body and body_path:
            body_path.parent.mkdir(exist_ok=True)
            body_temp = write_temp(body_path, change.body.text)
            temps.append(body_temp)
        if change.changes is not None:
            changes_temp = write_temp(changes_path, dump_yaml(change.changes))
            temps.append(changes_temp)
    except OSError as error:
        _remove_files(temps)
        raise write_failed(yaml_path, error) from error

    # 本文 → YAML → まとまりの順に置き換える
    try:
        if body_temp and body_path:
            os.replace(body_temp, body_path)
    except OSError as error:
        _remove_files(temps)
        raise write_failed(body_path or yaml_path, error) from error
    try:
        os.replace(yaml_temp, yaml_path)
    except OSError as error:
        # YAML を置き換えられなかった: 置き換えた本文を元に戻す
        if body_path and body_temp:
            _restore_body(body_path, previous_body)
        _remove_files(temps)
        raise write_failed(yaml_path, error) from error
    try:
        if changes_temp:
            os.replace(changes_temp, changes_path)
    except OSError as error:
        # まとまりを置き換えられなかった: 置き換えた YAML と本文を元に戻す
        _restore_file(yaml_path, previous_yaml)
        if body_path and body_temp:
            _restore_body(body_path, previous_body)
        _remove_files(temps)
        raise write_failed(changes_path, error) from error


def save_batch(workspace: Workspace, change: BatchChange) -> None:
    """複数の種類の項目の並びと本文とまとまりを、検証してから全て書き換えるか、どれも書き換えない。"""
    kinds = [kind for kind in KINDS if kind in change.items]
    # 書き戻すと中身を失う形のファイルには書かない（変更を当てる前の、そのファイルの問題を返す）
    for kind in kinds:
        if _loses_content_on_rewrite(workspace, kind):
            file_name = KINDS[kind].file
            current = [p for p in validate_workspace(workspace) if p.file == file_name]
            raise build_mismatch_error(current, workspace)
    # 変更を当てた後のワークスペース全体を検証する
    changed_raw = {
        **workspace.raw,
        **{KINDS[kind].file: {"items": change.items[kind]} for kind in kinds},
    }
    changed = replace(workspace, raw=changed_raw)
    problems = validate_workspace(changed)
    if problems:
        written_ids = frozenset().union(
            *(_written_ids(workspace.items[kind], change.items[kind]) for kind in kinds)
        )
        raise build_mismatch_error(problems, changed, written_ids=written_ids)

    # 置き換える順（本文 → 種類の YAML → まとまり）に、書く先と中身を並べる
    records = records_root(workspace.root)
    bodies = {body.name: body for body in change.bodies}
    targets: list[tuple[Path, str]] = [
        (records / BODY_DIR / body.name, body.text) for body in bodies.values()
    ]
    targets.extend(
        (records / KINDS[kind].file, dump_yaml({"items": change.items[kind]})) for kind in kinds
    )
    if change.changes is not None:
        targets.append((records / CHANGES_FILE, dump_yaml(change.changes)))
    # 置き換える前の中身を控える（無ければ None）
    previous = {path: path.read_bytes() if path.is_file() else None for path, _ in targets}

    # 一時ファイルを先に全て書く
    temps: list[Path] = []
    for path, text in targets:
        try:
            if path.parent.name == BODY_DIR:
                path.parent.mkdir(exist_ok=True)
            temps.append(write_temp(path, text))
        except OSError as error:
            _remove_files(temps)
            raise write_failed(path, error) from error

    # 順に置き換え、失敗したら置き換えたファイルを控えに戻す（前に無ければ消す）
    replaced: list[Path] = []
    for (path, _), temp in zip(targets, temps, strict=True):
        try:
            os.replace(temp, path)
        except OSError as error:
            for done in reversed(replaced):
                _restore_file(done, previous[done])
            _remove_files(temps)
            raise write_failed(path, error) from error
        replaced.append(path)


def create_workspace(root: Path, settings: dict[str, Any], *, version: str) -> list[str]:
    """設定を検証してから、`.mindstella/` に設定・空の 7 種類の YAML・版のファイル・`docs/`・`release/` を作り、直下に README を書く。"""
    root = root.resolve()
    records = records_root(root)
    if (records / SETTINGS_FILE).exists():
        raise WorkspaceExistsError(f"既にワークスペースがあります: {root}")
    # 直下に前の版の設定ファイルがあるフォルダも、記録を残したまま空の記録を作らない（移し替えを案内する）
    if (root / SETTINGS_FILE).exists() or (root / LEGACY_SETTINGS_FILE).exists():
        raise WorkspaceExistsError(
            f"既にワークスペースがあります: {root}",
            [UPGRADE_HINT.replace("{root}", str(root))],
        )

    # 設定と空の 7 種類で検証する（問題があればフォルダも作らない）
    raw: dict[str, Any] = {SETTINGS_FILE: settings}
    raw.update({spec.file: {"items": []} for spec in KINDS.values()})
    candidate = Workspace(
        root=root,
        raw=raw,
        settings=settings,
        items={kind: [] for kind in KINDS},
        load_problems=[],
    )
    problems = validate_workspace(candidate)
    if problems:
        raise build_mismatch_error(problems)

    # この関数が作ったファイルとフォルダ（途中で失敗したときに消す）
    created: list[Path] = []
    files: list[str] = []
    try:
        top_missing = _first_missing_ancestor(records)
        records.mkdir(parents=True, exist_ok=True)
        if top_missing is not None:
            created.append(top_missing)
        for dir_name in (BODY_DIR, RELEASE_DIR):
            _make_dir(records / dir_name, created)
            files.append(f"{RECORD_DIR}/{dir_name}/")
        for spec in KINDS.values():
            (records / spec.file).write_text(dump_yaml({"items": []}), encoding="utf-8")
            created.append(records / spec.file)
            files.append(f"{RECORD_DIR}/{spec.file}")
        (records / VERSION_FILE).write_text(f"{version}\n", encoding="utf-8")
        created.append(records / VERSION_FILE)
        files.append(f"{RECORD_DIR}/{VERSION_FILE}")
        # 直下の README は、前からあったものを失敗のときに消さないよう、無かったときだけ作ったものに数える
        readme_existed = (root / README_FILE).exists()
        readme_written = write_readme(root)
        if readme_written and not readme_existed:
            created.append(root / README_FILE)
        # config.yaml は最後に書く（途中で止まってもワークスペースとして扱われない）
        (records / SETTINGS_FILE).write_text(dump_yaml(settings), encoding="utf-8")
        files.append(f"{RECORD_DIR}/{SETTINGS_FILE}")
    except WriteFailedError:
        # README を書けなかった: 作ったものを消してそのまま送る
        _remove_created(created)
        raise
    except OSError as error:
        _remove_created(created)
        raise write_failed(root, error) from error
    # README は、この呼び出しで書いたときだけ末尾に載せる（利用者が書いたものは載せない）
    if readme_written:
        files.append(README_FILE)
    return files


def clear_release(root: Path) -> list[str]:
    """`.mindstella/release/` の中のファイルとフォルダを消す（`release/` が無ければ作る）。"""
    root = root.resolve()
    # .mindstella/config.yaml が無いフォルダはワークスペースではない（何も消さない）
    require_workspace(root)

    release_dir = records_root(root) / RELEASE_DIR
    removed: list[str] = []
    try:
        release_dir.mkdir(exist_ok=True)
    except OSError as error:
        raise write_failed(release_dir, error) from error
    # 名前の順に消す。消せないものに当たったら、そこで止める（それまでに消したものは戻さない）
    for path in sorted(release_dir.iterdir(), key=lambda entry: entry.name):
        # リンクでないフォルダは中身ごと、リンクとファイルはそのものを消す（リンク先は消さない）
        is_folder = path.is_dir() and not path.is_symlink()
        try:
            if is_folder:
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as error:
            raise write_failed(path, error) from error
        removed.append(f"{path.name}/" if is_folder else path.name)
    return removed


def read_body(workspace: Workspace, name: str) -> str | None:
    """`.mindstella/docs/` の本文を読む。ファイルが無いか、名前が `docs/` の外を指すときは None を返す。"""
    body_dir = (records_root(workspace.root) / BODY_DIR).resolve()
    path = (body_dir / name).resolve()
    # docs/ の外を指す名前は読まない
    if not path.is_relative_to(body_dir):
        return None
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def as_ids(value: Any) -> list[str]:
    """参照のキーの値（`parent` は文字列、ほかは配列）を ID の並びにする。"""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [element for element in value if isinstance(element, str)]
    return []


def dump_yaml(data: Any) -> str:
    """日本語をそのままにし、キーの並びを保って YAML の文字列にする。"""
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def _read_yaml(path: Path) -> Any:
    """1 ファイルを `yaml.safe_load` で読む（空のファイルは None）。"""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _extract_items(value: Any) -> list[dict[str, Any]]:
    """一番上が辞書で `items` が配列のときだけ、その要素のうち辞書のものを取り出す。"""
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        return []
    return [item for item in value["items"] if isinstance(item, dict)]


def _written_ids(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> frozenset[str]:
    """読んだ時点の並びと変更後の並びを比べ、足した項目と中身が違う項目の ID を返す。"""
    before_by_id = {item.get("id"): item for item in before}
    return frozenset(
        item["id"]
        for item in after
        if isinstance(item.get("id"), str)
        and (item["id"] not in before_by_id or before_by_id[item["id"]] != item)
    )


def _item_id_at(value: Any, path: list[str | int]) -> str | None:
    """キーのパスが `items[n]` の下を指すとき、その項目の ID を返す。"""
    if len(path) <= 1 or path[0] != "items" or not isinstance(path[1], int):
        return None
    items = value.get("items") if isinstance(value, dict) else None
    if not isinstance(items, list) or path[1] >= len(items):
        return None
    item = items[path[1]]
    item_id = item.get("id") if isinstance(item, dict) else None
    return item_id if isinstance(item_id, str) else None


def _path_order(path: list[str | int]) -> tuple[tuple[int, Any], ...]:
    """キーのパスを、添字は数の順・キーは名前の順で比べられる形にする。"""
    return tuple((0, part) if isinstance(part, int) else (1, part) for part in path)


def _format_path(path: Iterable[str | int]) -> str:
    """`absolute_path` を `items[0].status` の形の文字列にする。"""
    text = ""
    for part in path:
        # 添字は直前に `[n]` をつなぐ
        if isinstance(part, int):
            text += f"[{part}]"
        # キーは `.` でつなぐ（先頭は付けない）
        else:
            text += f".{part}" if text else part
    return text or WHOLE_PATH


def format_path(path: Iterable[str | int]) -> str:
    """`absolute_path` を `items[0].status` の形の文字列にする。"""
    return _format_path(path)


def remove_files(paths: list[Path]) -> None:
    """後始末として一時ファイルを消す（元の失敗を優先するので消せなくても続ける）。"""
    _remove_files(paths)


def write_temp(target: Path, text: str) -> Path:
    """置き換え先と同じフォルダに一時ファイルを書き、そのパスを返す（置き換えは呼ぶ側が行う）。"""
    return _write_temp(target, text)


def loses_content_on_rewrite(workspace: Workspace, kind: Kind) -> bool:
    """その種類のファイルが、項目の並びで書き戻すと中身を失う形かを返す。"""
    return _loses_content_on_rewrite(workspace, kind)


def _write_temp(target: Path, text: str) -> Path:
    """置き換え先と同じフォルダに一時ファイルを書き、置き換え先の権限に揃えてそのパスを返す。"""
    fd, name = tempfile.mkstemp(dir=target.parent, suffix=TEMP_SUFFIX)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        # mkstemp は 0600 で作るので、置き換えた後に権限が変わらないよう揃える
        if target.exists():
            # 置き換え先がある: その権限を写す
            shutil.copymode(target, temp)
        else:
            # 置き換え先が無い: 通常のファイルと同じ権限（0o666 から umask を引いたもの）にする
            temp.chmod(DEFAULT_FILE_MODE & ~_current_umask())
    except OSError:
        # 書けなかった一時ファイルは残さない
        _remove_files([temp])
        raise
    return temp


def _loses_content_on_rewrite(workspace: Workspace, kind: Kind) -> bool:
    """その種類のファイルが、項目の並びで書き戻すと中身を失う形か。

    読めない・一番上が辞書でない・`items` の横にキーがある・辞書でない要素がある、など
    `items` に取り出せない中身があるときに真になる。項目の中の値だけが合わない形は、変更で直せるので偽。
    """
    file_name = KINDS[kind].file
    # YAML として読めないファイル
    if any(problem.file == file_name for problem in workspace.load_problems):
        return True
    # 読んだ値が、取り出した項目の並びだけの形と違う
    return workspace.raw.get(file_name) != {"items": workspace.items[kind]}


def _current_umask() -> int:
    """今の umask を返す（読むには一度設定するしかないので、設定し直して戻す）。"""
    mask = os.umask(0)
    os.umask(mask)
    return mask


def _remove_files(paths: list[Path]) -> None:
    """後始末として一時ファイルを消す（元の失敗を優先するので消せなくても続ける）。"""
    for path in paths:
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)


def _restore_body(body_path: Path, previous_body: bytes | None) -> None:
    """置き換えた本文を、置き換える前の中身に戻す（前に本文が無ければ消す）。"""
    _restore_file(body_path, previous_body)


def _restore_file(path: Path, previous: bytes | None) -> None:
    """置き換えたファイルを、置き換える前の中身に戻す（前に無ければ消す）。"""
    # 前に無かった: 新しく書いたものを消す
    if previous is None:
        path.unlink(missing_ok=True)
        return
    path.write_bytes(previous)


def write_failed(path: Path, error: OSError) -> WriteFailedError:
    """置き換え先のパスと OSError の理由を持つ例外を作る。"""
    return WriteFailedError(f"書き込めませんでした: {path}（{error.strerror or error}）")


def _first_missing_ancestor(path: Path) -> Path | None:
    """まだ無いパスのうち、一番上のものを返す（全て在るときは None）。"""
    missing: Path | None = None
    current = path
    while not current.exists():
        missing = current
        current = current.parent
    return missing


def _make_dir(path: Path, created: list[Path]) -> None:
    """フォルダが無ければ作り、作ったものを記録する。"""
    if not path.exists():
        path.mkdir()
        created.append(path)


def _remove_created(created: list[Path]) -> None:
    """作ったファイルとフォルダを、作った順の逆に消す（元の失敗を優先するので消せなくても続ける）。"""
    for path in reversed(created):
        with contextlib.suppress(OSError):
            # フォルダは中身ごと、ファイルはそのものを消す
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
