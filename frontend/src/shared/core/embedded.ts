// 配る書き出しの 1 枚の HTML が持つ埋め込みの記録を読み、API の応答の代わりに返す

/** 記録の JSON を中身に持つ要素の ID */
export const EMBEDDED_DATA_ID = "mindmap-data";

/** 配る書き出しで、記録のほかに先読みする query のパスごとの空の応答 */
const EMPTY_RESPONSES = {
  "/api/comments": { items: [] },
  "/api/edits": { items: [] },
  "/api/threads": { threads: [] },
} as const satisfies Record<string, unknown>;

let cached: { data: unknown } | null | undefined;

/** 埋め込みの記録を返す。要素が無いか中身が空なら null。1 度読んだ結果を控える */
export const readEmbeddedData = (): unknown => {
  if (cached === undefined) {
    const text = document.getElementById(EMBEDDED_DATA_ID)?.textContent?.trim() ?? "";
    cached = text === "" ? null : { data: JSON.parse(text) as unknown };
  }
  return cached?.data ?? null;
};

/** 配る書き出しで開いているか */
export const isEmbedded = (): boolean => readEmbeddedData() !== null;

/** 配る書き出しで、GET の記録と空の応答を orval が期待する形で返す。ほかの要求は null */
export const embeddedResponse = ({ url, method }: { url: string; method: string }): { data: unknown; status: number; headers: Headers } | null => {
  if (method.toUpperCase() !== "GET") return null;
  const path = url.split("?")[0] ?? url;
  if (path === "/api/records") return { data: readEmbeddedData(), status: 200, headers: new Headers() };
  if (path in EMPTY_RESPONSES) return { data: EMPTY_RESPONSES[path as keyof typeof EMPTY_RESPONSES], status: 200, headers: new Headers() };
  return null;
};

/** テストの間で控えた埋め込みの記録を消す */
export const resetEmbeddedDataForTest = (): void => {
  cached = undefined;
};
