"""パスワードのハッシュの PoC: Argon2id で作り、使えなければ bcrypt に切り替え、接頭辞で照合の方式を選ぶ。

使い方:
  python poc.py [--block-argon2] --users {users.yaml のパス}
"""

from __future__ import annotations

import argparse
import importlib
import json
import resource
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

# 方式ごとのハッシュの接頭辞
ARGON2ID_PREFIX = "$argon2id$"
BCRYPT_PREFIXES = ("$2b$", "$2a$", "$2y$")

# 照合を測る回数
MEASURE_ROUNDS = 5

# 試すパスワードと、違うパスワード
GOOD_PASSWORD = "correct horse battery staple"
BAD_PASSWORD = "wrong password"


@dataclass(frozen=True, slots=True, kw_only=True)
class Hasher:
    """1 つの方式のハッシュの作り方と照合の仕方。"""

    scheme: str
    hash: Callable[[str], str]
    verify: Callable[[str, str], bool]


def _argon2_hasher() -> Hasher:
    """argon2-cffi の既定のパラメータで Argon2id のハッシュを作る方式を返す。"""
    argon2 = importlib.import_module("argon2")
    exceptions = importlib.import_module("argon2.exceptions")
    hasher = argon2.PasswordHasher()

    def verify(stored: str, password: str) -> bool:
        """保存したハッシュと照合する。違えば False。"""
        try:
            return bool(hasher.verify(stored, password))
        except exceptions.VerifyMismatchError:
            return False

    return Hasher(scheme="argon2id", hash=hasher.hash, verify=verify)


def _bcrypt_hasher() -> Hasher:
    """bcrypt の既定のコストでハッシュを作る方式を返す。"""
    bcrypt = importlib.import_module("bcrypt")

    def make(password: str) -> str:
        """新しいソルトでハッシュを作る。"""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")

    def verify(stored: str, password: str) -> bool:
        """保存したハッシュと照合する。"""
        return bool(bcrypt.checkpw(password.encode("utf-8"), stored.encode("ascii")))

    return Hasher(scheme="bcrypt", hash=make, verify=verify)


def select_hasher() -> tuple[Hasher, bool]:
    """新しく作るときの方式を選ぶ。Argon2id を import できなければ bcrypt にし、切り替えたかを返す。"""
    try:
        return _argon2_hasher(), False
    except ImportError:
        # argon2-cffi が入っていない: bcrypt に切り替える
        return _bcrypt_hasher(), True


def hasher_for(stored: str) -> Hasher:
    """保存したハッシュの接頭辞から照合の方式を選ぶ。"""
    if stored.startswith(ARGON2ID_PREFIX):
        return _argon2_hasher()
    if stored.startswith(BCRYPT_PREFIXES):
        return _bcrypt_hasher()
    raise ValueError(f"照合の方式が分からないハッシュです: {stored[:8]}")


def _peak_rss_kib() -> int:
    """このプロセスのこれまでの最大の常駐メモリ（KiB）を返す。"""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def measure(hasher: Hasher) -> dict[str, float]:
    """1 回の照合の時間（秒）と、ハッシュを作って照合するまでに増えた最大の常駐メモリ（KiB）を返す。"""
    before = _peak_rss_kib()
    stored = hasher.hash(GOOD_PASSWORD)
    durations = []
    for _ in range(MEASURE_ROUNDS):
        start = time.perf_counter()
        hasher.verify(stored, GOOD_PASSWORD)
        durations.append(time.perf_counter() - start)
    return {
        "verify_sec_max": max(durations),
        "verify_sec_min": min(durations),
        "peak_rss_increase_kib": _peak_rss_kib() - before,
    }


def run(users_path: Path) -> dict[str, object]:
    """方式を選んでハッシュを作り、users.yaml の全員を接頭辞で選んだ方式で照合する。"""
    hasher, switched = select_hasher()
    # 最初に測る（後の処理で最大の常駐メモリが先に上がらないように）
    measured = measure(hasher)
    stored = hasher.hash(GOOD_PASSWORD)
    result: dict[str, object] = {
        "scheme": hasher.scheme,
        "switched_to_bcrypt": switched,
        "prefix": stored.split("$")[1],
        "good_password_ok": hasher.verify(stored, GOOD_PASSWORD),
        "bad_password_rejected": not hasher.verify(stored, BAD_PASSWORD),
        "measure": measured,
    }

    # users.yaml に今の方式のハッシュを 1 人足し、全員を接頭辞で選んだ方式で照合する
    users = yaml.safe_load(users_path.read_text(encoding="utf-8")) if users_path.exists() else {}
    users = users or {}
    users[f"user-{hasher.scheme}"] = {"password_hash": stored}
    users_path.write_text(yaml.safe_dump(users, allow_unicode=True), encoding="utf-8")
    result["mixed_verify"] = {
        member_id: _verify_entry(entry["password_hash"]) for member_id, entry in users.items()
    }
    return result


def _verify_entry(stored: str) -> bool | str:
    """接頭辞で選んだ方式で照合する。方式のライブラリが入っていなければ、その旨を返す。"""
    try:
        verifier = hasher_for(stored)
    except ImportError:
        # Argon2id のハッシュだが argon2-cffi が入っていない: 照合できない
        return "照合できない（argon2-cffi が無い）"
    return verifier.verify(stored, GOOD_PASSWORD)


def main() -> int:
    """引数を読み、結果を JSON で標準出力に出す。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=Path, required=True)
    parser.add_argument("--block-argon2", action="store_true")
    args = parser.parse_args()
    # argon2 を import できない状態を作る
    if args.block_argon2:
        sys.modules["argon2"] = None  # type: ignore[assignment]
    print(json.dumps(run(args.users), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
