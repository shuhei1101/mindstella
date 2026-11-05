// React に無い画面を開くときの、今の画面の URL（インターフェース定義『プレビューの配信』）

/** 今の画面のパス */
export const LEGACY_PAGE_PATH = "/mindstella.html";

/** 今の画面のハッシュの引数（`tab`・`view`・`id`・`f.{列}`）から、今の画面の URL を組み立てる。値は URL エンコードする */
export const toLegacyUrl = (hash: Record<string, string>): string => {
  const pairs = Object.entries(hash).map(([key, value]) => `${key}=${encodeURIComponent(value)}`);
  return `${LEGACY_PAGE_PATH}#${pairs.join("&")}`;
};
