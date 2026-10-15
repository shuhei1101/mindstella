"""詳細パネル・詳細の全画面の見出しのタイトルの結合テストが共有する定数と JS。"""

from __future__ import annotations

# 見出しの帯に収まらない長さの題（先頭の語で確かめる。帯では省略記号付きで切れる）
HEAD_LONG_TITLE = (
    "話し合いの進め方の手引き（セットアップからヒアリング・リサーチ・方針転換を経て"
    "ゴール判定でリリースするまでの流れと、各段で記録に残すことの一覧）"
)

# 見出しのタイトルの先頭の語
HEAD_TITLE_PREFIX = "話し合いの進め方の手引き"

# 見出しのボタン（`.panel-head .icon-btn`）の幅（`--control-h`）
HEAD_BUTTON_WIDTH_PX = 32

# 出し入れの 0.15 秒の動きを終えるまで待つ上限ミリ秒
HEAD_TITLE_TIMEOUT_MS = 5_000

# 文字のフォントの読み込みと、パネルのすべり込みや出し入れの動きが全て終わるまで待つ（どちらも終わる前は幅や位置が動く）
ANIMATIONS_FINISHED_JS = """async () => {
    await document.fonts.ready;
    await Promise.all(document.getAnimations().map((animation) => animation.finished));
}"""

# 見出しのタイトルの出し入れが終わった状態（出す: 出ていて不透明 / 隠す: 出ていない）
HEAD_TITLE_SHOWN_JS = """(root) => {
    const title = document.querySelector(`${root} .panel-head .panel-title`);
    return title.classList.contains('is-shown') && getComputedStyle(title).opacity === '1';
}"""
HEAD_TITLE_HIDDEN_JS = """(root) => {
    const title = document.querySelector(`${root} .panel-head .panel-title`);
    return !title.classList.contains('is-shown') && getComputedStyle(title).visibility === 'hidden';
}"""

# 本文のスクロール領域を下端まで送る・先頭へ戻す
SCROLL_BODY_TO_END_JS = """(root) => {
    const body = document.querySelector(`${root} .panel-body`);
    body.scrollTop = body.scrollHeight;
}"""
SCROLL_BODY_TO_TOP_JS = """(root) => {
    document.querySelector(`${root} .panel-body`).scrollTop = 0;
}"""

# 見出しのタイトルの出方と、見出しの中の並びを測る。root は `aside.panel` か `dialog.full`
HEAD_METRICS_JS = """(root) => {
    const head = document.querySelector(`${root} .panel-head`);
    const title = head.querySelector('.panel-title');
    const style = getComputedStyle(title);
    const box = title.getBoundingClientRect();
    const kind = head.querySelector('.panel-kind').getBoundingClientRect();
    const badge = head.querySelector('.fmt-badge');
    // 幅の広い画面で隠れる「一覧へ戻る」は除き、表示されているボタンだけを測る
    const buttons = [...head.querySelectorAll('.icon-btn')]
        .filter((button) => button.getClientRects().length > 0)
        .map((button) => button.getBoundingClientRect());
    return {
        shown: title.classList.contains('is-shown'),
        visibility: style.visibility,
        text: title.textContent,
        titleAttr: title.getAttribute('title'),
        ariaHidden: title.getAttribute('aria-hidden'),
        textOverflow: style.textOverflow,
        whiteSpace: style.whiteSpace,
        truncated: title.scrollWidth > title.clientWidth,
        oneLine: box.height <= parseFloat(style.lineHeight) + 1,
        titleLeft: box.left,
        titleRight: box.right,
        kindRight: kind.right,
        badgeRight: badge === null ? null : badge.getBoundingClientRect().right,
        buttonWidths: buttons.map((button) => button.width),
        firstButtonLeft: Math.min(...buttons.map((button) => button.left)),
        lastButtonRight: Math.max(...buttons.map((button) => button.right)),
        headRight: head.getBoundingClientRect().right,
    };
}"""
