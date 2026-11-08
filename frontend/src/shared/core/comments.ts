// コメントの一覧・スレッド・レビュー中の書き込みの計算（今の画面の `screens/comments.ts`・`components/thread-row.ts` と同じ振る舞い）
import type { Location } from "@/shared/core/records";

/** スレッドの書き込み 1 件（`GET /api/threads` の `threads[].posts[]`） */
export type ThreadPostData = { id: string; author: "user" | "ai"; body: string; created: string; seen?: boolean };

/** スレッドの状態の記録 1 件（`threads[].events[]`） */
export type ThreadEvent = { kind: "closed" | "reopened"; author: "user" | "ai"; created: string; reason: string | null };

/** スレッド 1 件（`GET /api/threads` の `threads[]`） */
export type Thread = {
  id: string;
  status: "open" | "closed";
  summary: string | null;
  tags: string[];
  target: string | null;
  target_title?: string | null;
  loc: Location | null;
  posts: ThreadPostData[];
  events: ThreadEvent[];
};

/** レビュー中の書き込み 1 件（`GET /api/comments` の `items[]`。新しいスレッドの最初の書き込みか、スレッドへの返信） */
export type ReviewItem = {
  id: string;
  target: string | null;
  target_title?: string | null;
  loc: Location | null;
  thread: string | null;
  body: string;
  created: string;
};

/** 入力欄の書きかけ 1 件（`GET /api/comments` の `drafts[]`） */
export type Draft = { target: string | null; loc: Location | null; thread: string | null; body: string };

/** スレッドの状態の絞り込み */
export type ThreadFilter = "open" | "closed" | "all";

/** 書き込みと状態の記録を 1 本にした並びの 1 件 */
export type TimelineEntry = { post: ThreadPostData } | { event: ThreadEvent };

/** ID の連番（`C-12` は 12。読めなければ 0） */
const idNumber = (id: string): number => {
  const value = Number(id.replace(/^\D+-/, ""));
  return Number.isNaN(value) ? 0 : value;
};

/** コメントの ID の連番 */
export const commentNumber = (id: string): number => idNumber(id);

/** 日時の前後（ISO 8601 を時刻として比べる） */
const byTime = (a: string, b: string): number => Date.parse(a) - Date.parse(b);

/** スレッドの最後の書き込みの日時 */
const lastCreated = (thread: Thread): string => thread.posts.at(-1)?.created ?? "";

/** 行と見出しに出す題（要約。無ければ最初の書き込みの 1 行目） */
export const threadTitle = (thread: Thread): string => {
  if (thread.summary !== null && thread.summary !== "") return thread.summary;
  return (thread.posts[0]?.body ?? "").split("\n")[0] ?? "";
};

/** スレッドを状態とタグで絞り、最後の書き込みの新しい順に並べる（渡した配列は変えない） */
export const visibleThreads = ({ threads, filter, tag }: { threads: readonly Thread[]; filter: ThreadFilter; tag: string | null }): Thread[] =>
  threads
    .filter((thread) => filter === "all" || thread.status === filter)
    .filter((thread) => tag === null || thread.tags.includes(tag))
    .sort((a, b) => byTime(lastCreated(b), lastCreated(a)) || idNumber(b.id) - idNumber(a.id));

/** タグで絞ったスレッドの、状態の絞り込みに出す件数 */
export const threadCounts = ({ threads, tag }: { threads: readonly Thread[]; tag: string | null }): { open: number; closed: number; all: number } => {
  const tagged = tag === null ? threads : threads.filter((thread) => thread.tags.includes(tag));
  const open = tagged.filter((thread) => thread.status === "open").length;
  return { open, closed: tagged.length - open, all: tagged.length };
};

/** 一覧の先頭に出す、まだ送っていない新しいスレッド（クローズの絞り込みとタグの絞り込みでは出さない） */
export const pendingThreads = ({ items, filter, tag }: { items: readonly ReviewItem[]; filter: ThreadFilter; tag: string | null }): ReviewItem[] => {
  if (filter === "closed" || tag !== null) return [];
  return items.filter((item) => item.thread === null);
};

/** レビュー中の書き込みが、クローズのスレッドへの返信か（スレッドが見つからなければ偽） */
export const isBlockedReply = ({ item, threads }: { item: ReviewItem; threads: readonly Thread[] }): boolean => {
  if (item.thread === null) return false;
  return threads.find((thread) => thread.id === item.thread)?.status === "closed";
};

/** 書き込みと状態の記録を日時の順の 1 本の並びにする（同じ日時は書き込みを先にし、それぞれの中の並びを保つ） */
export const threadTimeline = (thread: Thread): TimelineEntry[] => {
  const entries = [
    ...thread.posts.map((post) => ({ entry: { post }, at: post.created, rank: 0 })),
    ...thread.events.map((event) => ({ entry: { event }, at: event.created, rank: 1 })),
  ];
  return entries.sort((a, b) => byTime(a.at, b.at) || a.rank - b.rank).map(({ entry }) => entry);
};

/** レビュー中の書き込みの読み上げの名前の頭 */
export const reviewLabel = (item: ReviewItem): string => {
  if (item.thread !== null) return `${item.thread} への返信`;
  return item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
};

/** 利用者の未読の書き込み（`seen` が偽）を持つか。`seen` を持たない書き込みは未読にしない */
export const hasUnseen = (thread: Thread): boolean => thread.posts.some((post) => post.seen === false);

/** トップバーの未読の点（オープンのスレッドに利用者の未読があるか） */
export const anyOpenUnseen = (threads: readonly Thread[]): boolean => threads.some((thread) => thread.status === "open" && hasUnseen(thread));

/** 指したスレッドの書き込みを全て既読にした新しい並び（渡した並びは書き換えない） */
export const withSeen = ({ threads, id }: { threads: readonly Thread[]; id: string }): Thread[] =>
  threads.map((thread) => (thread.id === id ? { ...thread, posts: thread.posts.map((post) => ({ ...post, seen: true })) } : thread));
