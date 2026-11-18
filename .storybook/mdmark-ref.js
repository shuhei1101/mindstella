// Storybook（.storybook/・.storybook-react/）を起動するときに、画面が読み込む mdmark の ref を決める。
// GitHub に mdmark の develop の先頭の commit の SHA を 1 回問い合わせ、問い合わせられなければ develop にする。

// develop の先頭の commit を問い合わせる URL
export const MDMARK_HEAD_URL = "https://api.github.com/repos/shuhei1101/mdmark/commits/develop";

// 問い合わせられないときに使う ref（サーバーの mdmark_ref.py の MDMARK_LATEST_BRANCH と同じ）
export const MDMARK_FALLBACK_REF = "develop";

// 1 回の問い合わせ全体を待つミリ秒（サーバーの接続 11 秒と読み取り 2 秒の合計。fetch は接続と読み取りを分けて待てない）
export const MDMARK_REF_TIMEOUT_MS = 13000;

// React の Storybook に ref を渡す meta 要素の名前（.storybook-react/preview.tsx が読む）
export const MDMARK_REF_META = "mindstella-mdmark-ref";

// commit の SHA の形
const COMMIT_SHA = /^[0-9a-f]{40}$/;

/** develop の先頭の commit の SHA を問い合わせて返す。問い合わせられなければ理由を 1 行出し、develop を返す */
export async function resolveMdmarkRef() {
  try {
    const response = await fetch(MDMARK_HEAD_URL, {
      headers: { Accept: "application/vnd.github.sha", "User-Agent": "mindstella" },
      signal: AbortSignal.timeout(MDMARK_REF_TIMEOUT_MS),
    });
    const body = (await response.text()).trim();
    // 200 で SHA の形の本文: その commit を読む
    if (response.ok && COMMIT_SHA.test(body)) return body;
    console.warn(`mdmark の develop の commit を問い合わせられないため ${MDMARK_FALLBACK_REF} を使います: HTTP ${response.status}`);
  } catch (error) {
    console.warn(`mdmark の develop の commit を問い合わせられないため ${MDMARK_FALLBACK_REF} を使います: ${String(error)}`);
  }
  return MDMARK_FALLBACK_REF;
}
