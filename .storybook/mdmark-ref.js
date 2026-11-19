// Storybook（.storybook/・.storybook-react/）を起動するときに、画面が読み込む mdmark の ref を決める。
// GitHub に mdmark の develop の先頭の commit の SHA を 1 回問い合わせ、jsDelivr がその配布物を配ることを確かめる。
// 問い合わせられない・配らなければ develop にする。

// develop の先頭の commit を問い合わせる URL
export const MDMARK_HEAD_URL = "https://api.github.com/repos/shuhei1101/mdmark/commits/develop";

// 問い合わせられないときに使う ref（サーバーの mdmark_ref.py の MDMARK_LATEST_BRANCH と同じ）
export const MDMARK_FALLBACK_REF = "develop";

// 1 回の問い合わせ全体を待つミリ秒（サーバーの接続 11 秒と読み取り 2 秒の合計。fetch は接続と読み取りを分けて待てない）
export const MDMARK_REF_TIMEOUT_MS = 13000;

// React の Storybook に ref を渡す meta 要素の名前（.storybook-react/preview.tsx が読む）
export const MDMARK_REF_META = "mindstella-mdmark-ref";

// 問い合わせた SHA の dist/index.js を jsDelivr が配るかを確認する URL（{ref} に SHA）
export const MDMARK_DIST_URL = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark@{ref}/dist/index.js";

// jsDelivr の確認全体を待つミリ秒（サーバーの jsDelivr の確認の接続 1 秒と読み取り 2 秒の合計）
export const MDMARK_DIST_TIMEOUT_MS = 3000;

// jsDelivr が配布物を配っていることを示すステータス
const SERVED_STATUSES = [200, 206];

// commit の SHA の形
const COMMIT_SHA = /^[0-9a-f]{40}$/;

/** develop の先頭の commit の SHA を問い合わせ、jsDelivr が配れば返す。問い合わせられない・配らなければ理由を 1 行出し、develop を返す */
export async function resolveMdmarkRef() {
  try {
    const response = await fetch(MDMARK_HEAD_URL, {
      headers: { Accept: "application/vnd.github.sha", "User-Agent": "mindstella" },
      signal: AbortSignal.timeout(MDMARK_REF_TIMEOUT_MS),
    });
    const body = (await response.text()).trim();
    if (!response.ok || !COMMIT_SHA.test(body)) {
      console.warn(`mdmark の develop の commit を問い合わせられないため ${MDMARK_FALLBACK_REF} を使います: HTTP ${response.status}`);
      return MDMARK_FALLBACK_REF;
    }
    // jsDelivr が配る: その commit を読む（本文は読まずに捨てる）
    const dist = await fetch(MDMARK_DIST_URL.replace("{ref}", body), {
      headers: { Range: "bytes=0-0", "User-Agent": "mindstella" },
      signal: AbortSignal.timeout(MDMARK_DIST_TIMEOUT_MS),
    });
    await dist.body?.cancel();
    if (SERVED_STATUSES.includes(dist.status)) return body;
    console.warn(`jsDelivr が mdmark の ${body} を配らないため ${MDMARK_FALLBACK_REF} を使います: HTTP ${dist.status}`);
  } catch (error) {
    console.warn(`mdmark の develop の commit を問い合わせられないため ${MDMARK_FALLBACK_REF} を使います: ${String(error)}`);
  }
  return MDMARK_FALLBACK_REF;
}
