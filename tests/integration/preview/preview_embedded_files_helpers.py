"""資料に埋め込んだ動画・画像を画面で描く結合テストが共有する、ファイルの中身・本文と配置の関数。"""

from __future__ import annotations

import base64
from pathlib import Path


# 1 秒の VP9 の動画（mp4 の入れ物。Chromium がプロプライエタリのコーデック無しで再生できる）
CLIP_MP4 = base64.b64decode(
    "AAAAHGZ0eXBpc29tAAACAGlzb21pc28ybXA0MQAAAAhmcmVlAAAAuG1kYXSCSYNCAAPwA/YAOCQcGEIAADBgAABn"
    "P///NTN/////7FMH////46dRMIYAQJKcAElAAAMgAABUcIYAQJKcAErAAAMgAABUcIYAQJKcAEnAAAMgAABUcIYA"
    "QJKcAEigAAMgAABUcIYAQJKcAEeAAAMgAABUcIYAQJKcAEbgAAMgAABUcIYAQJKcAEZAAAMgAABUcIYAQJKcAEXA"
    "AAMgAABUcIYAQJKcAEVAAAMgAABUcAAAAzttb292AAAAbG12aGQAAAAAAAAAAAAAAAAAAAPoAAAD6AABAAABAAAA"
    "AAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAACAAACZXRyYWsAAABcdGtoZAAAAAMAAAAAAAAAAAAAAAEAAAAAAAAD6AAAAAAAAAAAAAAAAAAAAAAAAQAA"
    "AAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAEAAAAAAQAAAAEAAAAAAACRlZHRzAAAAHGVsc3QAAAAAAAAAAQAA"
    "A+gAAAAAAAEAAAAAAd1tZGlhAAAAIG1kaGQAAAAAAAAAAAAAAAAAACgAAAAoAFXEAAAAAAAtaGRscgAAAAAAAAAA"
    "dmlkZQAAAAAAAAAAAAAAAFZpZGVvSGFuZGxlcgAAAAGIbWluZgAAABR2bWhkAAAAAQAAAAAAAAAAAAAAJGRpbmYA"
    "AAAcZHJlZgAAAAAAAAABAAAADHVybCAAAAABAAABSHN0YmwAAACoc3RzZAAAAAAAAAABAAAAmHZwMDkAAAAAAAAA"
    "AQAAAAAAAAAAAAAAAAAAAAAAQABAAEgAAABIAAAAAAAAAAEYTGF2YzYwLjMxLjEwMiBsaWJ2cHgtdnA5AAAAAAAA"
    "AAAY//8AAAAUdnBjQwEAAAAACoICAgIAAAAAAApmaWVsAQAAAAAQcGFzcAAAAAEAAAABAAAAFGJ0cnQAAAAAAABO"
    "IAAABYAAAAAYc3R0cwAAAAAAAAABAAAACgAABAAAAAAUc3RzcwAAAAAAAAABAAAAAQAAABxzdHNjAAAAAAAAAAEA"
    "AAABAAAACgAAAAEAAAA8c3RzegAAAAAAAAAAAAAACgAAACkAAAAPAAAADwAAAA8AAAAPAAAADwAAAA8AAAAPAAAA"
    "DwAAAA8AAAAUc3RjbwAAAAAAAAABAAAALAAAAGJ1ZHRhAAAAWm1ldGEAAAAAAAAAIWhkbHIAAAAAAAAAAG1kaXJh"
    "cHBsAAAAAAAAAAAAAAAALWlsc3QAAAAlqXRvbwAAAB1kYXRhAAAAAQAAAABMYXZmNjAuMTYuMTAw"
)

# 8×8 の png の画像
SHOT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAACXBIWXMAAAABAAAAAQBPJcTWAAAAEklEQVR4nGP4"
    "y8CAFWEXHbQSAPZwP0G2GkFNAAAAAElFTkSuQmCC"
)

# 動画・画像と、インラインコードの中のパスを埋め込んだ資料の本文
EMBEDDED_FILES_BODY = (
    "![動画](../files/clip.mp4)\n\n"
    "![画面](../files/shot.png)\n\n"
    "`![x](../files/x.png)` は書いたまま出る\n"
)

# 本文の中の動画・画像の要素と、インラインコード
BODY_VIDEO = "aside.panel .md:not(.md-value) video"
BODY_IMAGE = "aside.panel .md:not(.md-value) img"
BODY_CODE = "aside.panel .md:not(.md-value) code"

# 動画のメタデータが読み込まれ、画像の読み込みが終わったことを確かめる JavaScript（真偽値を返却する）
MEDIA_READY_JS = (
    "([video, image]) => {"
    " const v = document.querySelector(video); const i = document.querySelector(image);"
    " return v !== null && i !== null && v.readyState >= 1 && v.error === null"
    " && i.complete && i.naturalWidth > 0; }"
)


def put_embedded_files(root: Path) -> None:
    """ワークスペースのファイルのフォルダに、動画 `clip.mp4` と画像 `shot.png` を配置する。"""
    files = root / "files"
    files.mkdir(parents=True, exist_ok=True)
    (files / "clip.mp4").write_bytes(CLIP_MP4)
    (files / "shot.png").write_bytes(SHOT_PNG)
