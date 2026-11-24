// 資料の本文の Markdown の見出しから作る目次
import { headingSlug } from "@/shared/core/body-links";

/** 目次の項目 1 つ */
export type TocEntry = { level: number; text: string; slug: string };

/** 見出しの行（`#` 1〜6 個と空白の後に文言） */
const HEADING_LINE = /^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$/;

/** コードブロックの囲みの行 */
const FENCE_LINE = /^[ \t]{0,3}(`{3,}|~{3,})/;

/** 見出しの文言から、描いた見出しに出る文字だけを残す（リンクは文言、強調・行内のコードの記号は除外する） */
const plainText = (text: string): string =>
  text
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/[*_`~]/g, "")
    .trim();

/** 本文の Markdown の見出しを、本文の順に階層と見出しを指す名前つきで返却する。コードブロックの中の `#` の行は見出しにしない */
export const bodyToc = (markdown: string): TocEntry[] => {
  const entries: TocEntry[] = [];
  const seen = new Map<string, number>();
  let fence: string | null = null;
  for (const line of markdown.split("\n")) {
    const mark = FENCE_LINE.exec(line)?.[1]?.charAt(0);
    if (mark !== undefined) {
      if (fence === null) fence = mark;
      else if (mark === fence) fence = null;
      continue;
    }
    if (fence !== null) continue;
    const [, hashes = "", raw = ""] = HEADING_LINE.exec(line) ?? [];
    const text = plainText(raw);
    if (hashes === "" || text === "") continue;
    entries.push({ level: hashes.length, text, slug: headingSlug({ text, seen }) });
  }
  return entries;
};
