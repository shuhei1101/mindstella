"""資料・調査のエイリアスの本文の印とツールチップの結合テストが共通で使う、記録・本文・選び方。"""

from __future__ import annotations

from preview_fixture_types import WritePreview
from workspace_fixtures import MakeItem

# 本文の印の選び方（詳細パネルと全画面）と、ツールチップ
PANEL_MARKS = "aside.panel .md:not(.md-value) p a.term"
FULL_MARKS = "dialog.full .md:not(.md-value) p a.term"
TIP = "#term-tip"
TIP_OPEN = "#term-tip:popover-open"

# 本文: 見出し（印を付けない）、用語・エイリアス・取り下げた資料だけのエイリアス・自分のエイリアスを並べた段落、
# 中身がちょうど語のインラインコードと語を含むだけのインラインコード、コードブロック
ALIAS_BODY = (
    "## 特殊効果の見出し\n\n"
    "特殊効果とエフェクトと古い語と保存先と自分の別名\n\n"
    "`特殊効果` と `特殊効果の設定`\n\n"
    "```\n特殊効果\n```\n"
)

# 「特殊効果」の印に一致する項目の ID（用語 → 資料 → 調査の順。取り下げた資料 A-8 と開いている A-1 は含まない）
MIXED_IDS = "G-1 A-2 A-3 R-1"

# 本文を送った後に、最初の印を本文の領域の上端から下へ置く距離（px）。ツールチップの高さより上の余白が狭く、印が領域の中に見える
MARK_MARGIN_PX = 40

# 本文の上の要素はフォントの読み込みで高さが変わるので、読み終えて印の位置が 150ms 続けて同じになるまで待ってから、
# 最初の印が本文の領域の上端から margin だけ下に来るよう送る
SCROLL_MARK_NEAR_TOP_JS = """async (margin) => {
  const body = document.querySelector('aside.panel .panel-body');
  const mark = document.querySelector('aside.panel .md a.term');
  const offset = () => mark.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop;
  await document.fonts.ready;
  let last = -1;
  while (offset() !== last) {
    last = offset();
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  body.scrollTop = last - margin;
}"""

# 最初の印が本文の領域の中に見えているか（hover の直前の本文の位置と合わせて返す）
MARK_IN_PANEL_BODY_JS = """() => {
  const body = document.querySelector('aside.panel .panel-body');
  const area = body.getBoundingClientRect();
  const mark = document.querySelector('aside.panel .md a.term').getBoundingClientRect();
  return {scrollTop: body.scrollTop, inside: mark.top >= area.top && mark.bottom <= area.bottom};
}"""


def write_alias_preview(
    write_preview: WritePreview,
    make_item: MakeItem,
    *,
    extra_docs: int = 0,
    body: str = ALIAS_BODY,
) -> str:
    """本文を持つ資料 A-1 と、エイリアスを持つ資料・調査・用語の配信の URL を返す。

    extra_docs は、エイリアス「特殊効果」を持つ資料を A-10 から足す件数。
    """
    extra = [
        make_item(
            f"A-{number}",
            title=f"追加の資料 {number}",
            aliases=["特殊効果"],
            description=f"追加の資料 {number} の説明",
        )
        for number in range(10, 10 + extra_docs)
    ]
    return write_preview(
        make_item("A-1", aliases=["自分の別名"]),
        make_item(
            "A-2",
            title="特殊効果のスキーマ",
            aliases=["特殊効果", "エフェクト"],
            description="特殊効果の設定ファイルのキーと型",
        ),
        make_item("A-3", title="炎ノード", aliases=["特殊効果"]),
        make_item("A-8", title="古い資料", aliases=["古い語", "特殊効果"], withdrawn=True),
        *extra,
        make_item(
            "R-1",
            title="特殊効果を重ねたときの描画の負荷",
            aliases=["特殊効果"],
            description="ノードを 1〜8 個重ねたときの測り方と結果",
        ),
        make_item("G-1", title="特殊効果", meaning="画面に重ねる演出"),
        make_item("G-2", title="保存先", meaning="記録を置く場所"),
        bodies={"A-1.md": body, "A-2.md": "資料 A-2 の本文の段落\n"},
    )


# 本文: 別名・タイトルと同じ別名・2 つの用語が持つ同じ別名・取り下げた用語の別名を並べた段落
TERM_ALIAS_BODY = "マイグレーションと移し替えと古い呼び方\n"

# 「移し替え」の印に一致する用語の ID（G-1 はタイトルと別名の両方が同じ語だが 1 回だけ数える）
SHARED_TERM_IDS = "G-1 G-2"


def write_term_alias_preview(write_preview: WritePreview, make_item: MakeItem) -> str:
    """本文を持つ資料 A-1 と、別名を持つ用語 G-1・G-2・取り下げた G-3 の配信の URL を返す。"""
    return write_preview(
        make_item("A-1"),
        make_item(
            "G-1",
            title="移し替え",
            aliases=["マイグレーション", "移し替え", " "],
            meaning="記録を今の版に直すこと",
        ),
        make_item("G-2", title="版の更新", aliases=["移し替え"], meaning="版を上げること"),
        make_item("G-3", title="旧名", aliases=["古い呼び方"], meaning="今は使わない用語", withdrawn=True),
        bodies={"A-1.md": TERM_ALIAS_BODY},
    )
