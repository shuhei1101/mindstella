"""起動スクリプトを呼ぶ alias と環境変数を、ログインシェルの設定に登録・読み返し・外す。

MCP のツールも mindstella の仮想環境も無い状態で、システムの `python3` で起動するため、
Python 3.8 で読める構文と標準ライブラリだけで書く。
使い方（セットアップのスキルが Bash で呼ぶ）:
  python3 register.py {show|set|add-account|remove-account|remove} [--env KEY=VALUE]... [--unset-env KEY]... [--name 名前] [--config-dir フォルダ]
標準出力にその後の登録を JSON で出す。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

# `--env`・`--unset-env` で受ける環境変数のキー（`shell.sh` にはこの順で書く）
ENV_KEYS = (
    "MINDSTELLA_VENV",
    "MINDSTELLA_ALLOWED_HOSTS",
    "MINDSTELLA_PREVIEW_START_HOOK",
    "MINDSTELLA_PREVIEW_STOP_HOOK",
)

# 既定のアカウントで立ち上げる alias の名前（アカウントごとの alias は `{ALIAS_NAME}-{名前}`）
ALIAS_NAME = "mindstella"

# アカウントの名前の形
ACCOUNT_NAME_PATTERN = r"^[a-z0-9][a-z0-9-]{0,31}$"

# ログインシェルの設定ファイルに足す範囲の頭と尾の行
MARK_BEGIN = "# >>> mindstella >>>"
MARK_END = "# <<< mindstella <<<"

# alias が `claude plugin list --json` の要素の `id` で引く値（`launch.py` の同じ名前の定数と合わせる）
PLUGIN_ID = "mindstella@mindstella"

# 登録の中身を書くファイルと、alias と環境変数を書くファイルの名前
REGISTRATION_FILE = "registration.json"
SHELL_FILE = "shell.sh"

# 新しく作るファイルの権限
NEW_FILE_MODE = 0o644

# alias が `claude plugin list --json` の出力から `installPath` を引く Python のコード
FIND_INSTALL_PATH = (
    "import json, sys\n"
    "try:\n"
    "    items = json.load(sys.stdin)\n"
    "except ValueError:\n"
    "    items = []\n"
    "for item in items if isinstance(items, list) else []:\n"
    '    if isinstance(item, dict) and item.get("id") == "' + PLUGIN_ID + '":\n'
    '        print(item.get("installPath", ""))\n'
    "        break\n"
)


class Registration(TypedDict):
    """`registration.json` に残す登録の中身。`shell.sh` はここから作る。"""

    env: dict[str, str]
    accounts: list[dict[str, str]]


class NotWritableError(Exception):
    """ログインシェルの設定ファイルか登録の置き場所に書き込めない。"""

    def __init__(self, path: Path) -> None:
        """書き込めないファイルかフォルダを控える。"""
        super().__init__(f"{path} に書き込めません")
        self.path = path


class UnsupportedShellError(Exception):
    """`SHELL` の末尾の名前が `bash`・`zsh` のどちらでもない。"""

    def __init__(self, shell: str) -> None:
        """`SHELL` の値を控える。"""
        super().__init__(f"シェル {shell} には登録できません。bash か zsh で呼んでください")
        self.shell = shell


class UnknownAccountError(Exception):
    """`remove-account` の名前が登録に無い。"""

    def __init__(self, name: str, known: list[str]) -> None:
        """登録済みのアカウントの名前を控える。"""
        super().__init__(f"アカウント {name} は登録されていません（登録済み: {'、'.join(known)}）")
        self.known = known


def registration_dir(environ: Mapping[str, str]) -> Path:
    """`registration.json` と `shell.sh` を置くフォルダを返す。"""
    config_home = environ.get("XDG_CONFIG_HOME")
    # XDG_CONFIG_HOME が無いか空なら、ホームの .config
    base = Path(config_home) if config_home else Path(environ["HOME"]) / ".config"
    return base / "mindstella"


def rc_file_path(environ: Mapping[str, str], *, system: str) -> Path:
    """`SHELL` と OS から、印の範囲を足すログインシェルの設定ファイルを決める。"""
    shell = environ.get("SHELL", "")
    name = shell.rsplit("/", 1)[-1]
    home = Path(environ["HOME"])
    if name == "bash":
        # macOS のターミナルは bash をログインシェルで開き、~/.bashrc を読まない
        return home / (".bash_profile" if system == "Darwin" else ".bashrc")
    if name == "zsh":
        return home / ".zshrc"
    raise UnsupportedShellError(shell)


def read_registration(directory: Path) -> Registration | None:
    """登録の置き場所の `registration.json` を読む。無ければ `None`（読めない JSON はそのまま送る）。"""
    path = directory / REGISTRATION_FILE
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def apply_set(
    registration: Registration, *, updates: dict[str, str], removals: list[str]
) -> Registration:
    """渡したキーだけを書き換え・外した登録を返す（渡した登録は変えない）。"""
    env = dict(registration["env"])
    env.update(updates)
    for key in removals:
        env.pop(key, None)
    return {"env": env, "accounts": [dict(a) for a in registration["accounts"]]}


def apply_add_account(registration: Registration, *, name: str, config_dir: Path) -> Registration:
    """アカウントを足した登録を返す。同じ名前があれば設定のフォルダを書き換える。"""
    others = [dict(a) for a in registration["accounts"] if a["name"] != name]
    accounts = [*others, {"name": name, "config_dir": str(config_dir)}]
    accounts.sort(key=lambda account: account["name"])
    return {"env": dict(registration["env"]), "accounts": accounts}


def apply_remove_account(registration: Registration | None, *, name: str) -> Registration:
    """アカウントを外した登録を返す。"""
    known = [] if registration is None else [a["name"] for a in registration["accounts"]]
    # 登録が無いか、そのアカウントが無い
    if registration is None or name not in known:
        raise UnknownAccountError(name, known)
    return {
        "env": dict(registration["env"]),
        "accounts": [dict(a) for a in registration["accounts"] if a["name"] != name],
    }


def _shell_quote(value: str) -> str:
    """シェルの単引用符で囲む（値の `'` は `'\\''` に置き換える）。"""
    return "'" + value.replace("'", "'\\''") + "'"


def render_shell(registration: Registration) -> str:
    """登録から `shell.sh` の中身（`export` と alias の関数）を作る。bash と zsh のどちらでも読める。"""
    lines: list[str] = []
    # 登録した環境変数を ENV_KEYS の順に書く
    for key in ENV_KEYS:
        if key in registration["env"]:
            lines.append(f"export {key}={_shell_quote(registration['env'][key])}")
    # 叩くたびに今の installPath を引いて起動スクリプトへ引数を渡す内部の関数
    lines.extend(
        [
            "_mindstella_run() {",
            '  local _ms_dir="$1" _ms_path',
            "  shift",
            '  if [ -n "$_ms_dir" ]; then',
            '    _ms_path=$(CLAUDE_CONFIG_DIR="$_ms_dir" command claude plugin list --json'
            f" 2>/dev/null | python3 -c {_shell_quote(FIND_INSTALL_PATH)})",
            "  else",
            "    _ms_path=$(command claude plugin list --json"
            f" 2>/dev/null | python3 -c {_shell_quote(FIND_INSTALL_PATH)})",
            "  fi",
            '  if [ -z "$_ms_path" ]; then',
            f'    echo "[mindstella] エラー: プラグイン {PLUGIN_ID} の場所を引けません" >&2',
            "    return 1",
            "  fi",
            '  if [ -n "$_ms_dir" ]; then',
            '    CLAUDE_CONFIG_DIR="$_ms_dir" "$_ms_path/bin/mindstella" "$@"',
            "  else",
            '    "$_ms_path/bin/mindstella" "$@"',
            "  fi",
            "}",
            f"{ALIAS_NAME}() {{ _mindstella_run '' \"$@\"; }}",
        ]
    )
    # アカウントごとの alias は、そのアカウントの設定のフォルダを渡す
    for account in registration["accounts"]:
        quoted_dir = _shell_quote(account["config_dir"])
        lines.append(f'{ALIAS_NAME}-{account["name"]}() {{ _mindstella_run {quoted_dir} "$@"; }}')
    return "\n".join(lines) + "\n"


def add_rc_block(text: str, *, shell_file: Path) -> str:
    """設定ファイルの中身に、`shell.sh` を読み込む印の範囲が無ければ末尾に足す。"""
    # 既に足してある
    if MARK_BEGIN in text.splitlines():
        return text
    quoted = _shell_quote(str(shell_file))
    block = f"{MARK_BEGIN}\n[ -f {quoted} ] && . {quoted}\n{MARK_END}\n"
    # 空でなければ、末尾の改行の有無によらず改行を 1 つ挟む（消すときにその改行を戻す）
    return text + "\n" + block if text else block


def remove_rc_block(text: str) -> str:
    """設定ファイルの中身から印の範囲を消す。範囲の外の行と、足したときの改行は元に戻す。"""
    lines = text.splitlines(keepends=True)
    heads = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == MARK_BEGIN]
    # 範囲が無い
    if not heads:
        return text
    begin = heads[0]
    tails = [i for i in range(begin, len(lines)) if lines[i].rstrip("\r\n") == MARK_END]
    # 尾が無い壊れた範囲は触らない
    if not tails:
        return text
    before = "".join(lines[:begin])
    after = "".join(lines[tails[0] + 1 :])
    # add_rc_block が足した改行を 1 つ戻す
    if before.endswith("\n"):
        before = before[:-1]
    return before + after


def _nearest_existing(path: Path) -> Path:
    """path か、あるところまでの親のフォルダを返す。"""
    current = path
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def write_files(contents: dict[Path, str | None]) -> None:
    """ファイルごとの中身を、全て書けると確かめてから書く。中身が `None` のファイルは消す。"""
    # 書く先がシンボリックリンクなら、リンクを残してリンク先を書き換える
    targets: dict[Path, str | None] = {}
    for path, text in contents.items():
        targets[Path(os.path.realpath(path)) if path.is_symlink() else path] = text
    # 書く前に、全ての書く先に書き込めるかを確かめる
    for path, text in targets.items():
        if text is None and not path.exists():
            continue
        if path.exists() and not os.access(str(path), os.W_OK):
            raise NotWritableError(path)
        parent = _nearest_existing(path.parent)
        if not os.access(str(parent), os.W_OK | os.X_OK):
            raise NotWritableError(path)
    # 同じフォルダの一時ファイルに書いてから置き換える
    for path, text in targets.items():
        if text is None:
            if path.exists():
                path.unlink()
            continue
        temp_name: str | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".mindstella-")
            with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
                stream.write(text)
            # 既にあれば元の権限を写し、無ければ既定の権限にする
            if path.exists():
                shutil.copymode(str(path), temp_name)
            else:
                os.chmod(temp_name, NEW_FILE_MODE)
            os.replace(temp_name, str(path))
        except OSError as error:
            # 書きかけの一時ファイルを残さない
            if temp_name is not None and os.path.exists(temp_name):
                os.unlink(temp_name)
            raise NotWritableError(path) from error


def build_report(
    registration: Registration | None, *, rc_file: Path, shell_file: Path
) -> dict[str, Any]:
    """登録から、標準出力に出す JSON を作る。"""
    env = {} if registration is None else registration["env"]
    accounts = [] if registration is None else registration["accounts"]
    aliases: list[str] = []
    # 登録があれば、既定の alias とアカウントごとの alias を並べる
    if registration is not None:
        aliases = [ALIAS_NAME] + [f"{ALIAS_NAME}-{a['name']}" for a in accounts]
    return {
        "registered": registration is not None,
        "rc_file": str(rc_file),
        "shell_file": str(shell_file),
        "env": env,
        "accounts": accounts,
        "aliases": aliases,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """サブコマンドとオプションを解釈する。"""
    parser = argparse.ArgumentParser(description="起動スクリプトの alias と環境変数の登録")
    parser.add_argument(
        "command", choices=["show", "set", "add-account", "remove-account", "remove"]
    )
    parser.add_argument("--env", action="append", default=[], help="KEY=VALUE")
    parser.add_argument("--unset-env", action="append", default=[], help="KEY")
    parser.add_argument("--name")
    parser.add_argument("--config-dir")
    return parser.parse_args(argv)


def _usage_error(message: str) -> int:
    """使い方の誤りを標準エラーに出して 2 を返す。"""
    print(f"使い方の誤り: {message}", file=sys.stderr)
    return 2


def _check_args(args: argparse.Namespace) -> str | None:
    """引数の誤りを 1 つ返す。誤りが無ければ `None`。"""
    for item in args.env:
        key, separator, value = item.partition("=")
        if not separator:
            return f"--env は KEY=VALUE の形で渡してください: {item}"
        if key not in ENV_KEYS:
            return f"--env のキーは {' / '.join(ENV_KEYS)} のどれかです: {key}"
        if "\n" in value:
            return f"--env の値に改行は入れられません: {key}"
    for key in args.unset_env:
        if key not in ENV_KEYS:
            return f"--unset-env のキーは {' / '.join(ENV_KEYS)} のどれかです: {key}"
    if args.name is not None and not re.match(ACCOUNT_NAME_PATTERN, args.name):
        return f"--name は英小文字・数字・- の 1〜32 文字で、英小文字か数字で始めてください: {args.name}"
    if args.command == "add-account" and (args.name is None or args.config_dir is None):
        return "add-account には --name と --config-dir が要ります"
    if args.command == "remove-account" and args.name is None:
        return "remove-account には --name が要ります"
    return None


def _absolute_dir(text: str, environ: Mapping[str, str]) -> Path:
    """`~` をホームに直した絶対パスにする。"""
    if text == "~" or text.startswith("~/"):
        text = environ["HOME"] + text[1:]
    return Path(os.path.abspath(text))


def _manual_lines(registration: Registration) -> list[str]:
    """手でログインシェルの設定ファイルに書けば同じ登録になる行（印の範囲と alias の定義）を返す。"""
    return [MARK_BEGIN, *render_shell(registration).splitlines(), MARK_END]


def _print_json(value: dict[str, Any]) -> None:
    """JSON を標準出力に出す。"""
    print(json.dumps(value, ensure_ascii=False))


def _read_text(path: Path) -> str:
    """ファイルがあれば中身を、無ければ空を返す。"""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    system: str = platform.system(),
) -> int:
    """サブコマンドを解釈して登録を読む・書く・外し、その後の登録を JSON で標準出力に出して終了コードを返す。"""
    try:
        args = _parse_args(argv)
    except SystemExit as exit_request:
        # argparse が使い方を標準エラーに出して終えようとした
        return int(exit_request.code or 0)
    problem = _check_args(args)
    if problem is not None:
        return _usage_error(problem)

    directory = registration_dir(environ)
    shell_file = directory / SHELL_FILE
    registration_file = directory / REGISTRATION_FILE
    try:
        current = read_registration(directory)
    except ValueError:
        # registration.json を JSON として読めない: 何も書かない
        _print_json({"error": f"{registration_file} を読めません"})
        return 1

    empty: Registration = {"env": {}, "accounts": []}
    updated = current
    try:
        if args.command == "set":
            updates = dict(item.split("=", 1) for item in args.env)
            updated = apply_set(current or empty, updates=updates, removals=args.unset_env)
        elif args.command == "add-account":
            config_dir = _absolute_dir(args.config_dir, environ)
            updated = apply_add_account(current or empty, name=args.name, config_dir=config_dir)
        elif args.command == "remove-account":
            updated = apply_remove_account(current, name=args.name)
        elif args.command == "remove":
            updated = None
    except UnknownAccountError as error:
        _print_json({"error": str(error)})
        return 1

    try:
        rc_file = rc_file_path(environ, system=system)
    except UnsupportedShellError as error:
        _print_json({"error": str(error), "manual_lines": _manual_lines(updated or empty)})
        return 1

    # show は何も書かない
    if args.command != "show":
        rc_text = _read_text(rc_file)
        if updated is None:
            contents: dict[Path, str | None] = {registration_file: None, shell_file: None}
            # 設定ファイルがあって範囲を持つときだけ書き換える
            removed = remove_rc_block(rc_text)
            if rc_file.exists() and removed != rc_text:
                contents[rc_file] = removed
        else:
            contents = {
                registration_file: json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
                shell_file: render_shell(updated),
            }
            added = add_rc_block(rc_text, shell_file=shell_file)
            # 設定ファイルが無いか、足す中身があるときだけ書く
            if not rc_file.exists() or added != rc_text:
                contents[rc_file] = added
        try:
            write_files(contents)
        except NotWritableError as error:
            _print_json({"error": str(error), "manual_lines": _manual_lines(updated or empty)})
            return 1

    _print_json(build_report(updated, rc_file=rc_file, shell_file=shell_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
