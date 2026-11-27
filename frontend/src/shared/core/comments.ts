// コメントの一覧・スレッド・レビュー中の書き込みの計算
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

/** レビュー中の書き込み 1 件（`GET /api/comments` の `items[]`。新規スレッドの最初の書き込みか、スレッドへの返信） */
export type ReviewItem = {
  id: string;
  target: string | null;
  target_title?: string | null;
  loc: Location | null;
  thread: string | null;
  /** 本文（一言を添えない案の選択は null） */
  body: string | null;
  /** 案の選択の選んだ案（案の選択でないコメントは持たない） */
  choice?: { key: string } | null;
  created: string;
};

/** 入力欄の下書き 1 件（`GET /api/comments` の `drafts[]`） */
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
export const visibleThreads = ({ threads, filter, tag, target }: { threads: readonly Thread[]; filter: ThreadFilter; tag: string | null; target: string | null }): Thread[] =>
  threads
    .filter((thread) => filter === "all" || thread.status === filter)
    .filter((thread) => tag === null || thread.tags.includes(tag))
    .filter((thread) => target === null || thread.target === target)
    .sort((a, b) => byTime(lastCreated(b), lastCreated(a)) || idNumber(b.id) - idNumber(a.id));

/** タグと項目で絞ったスレッドの、状態の絞り込みに出す件数 */
export const threadCounts = ({ threads, tag, target }: { threads: readonly Thread[]; tag: string | null; target: string | null }): { open: number; closed: number; all: number } => {
  const tagged = threads.filter((thread) => (tag === null || thread.tags.includes(tag)) && (target === null || thread.target === target));
  const open = tagged.filter((thread) => thread.status === "open").length;
  return { open, closed: tagged.length - open, all: tagged.length };
};

/** 一覧の先頭に出す、まだ送っていない新規スレッド（案の選択は除く。クローズの絞り込みとタグの絞り込みでは出さない。項目で絞っている間はその項目へのものだけ） */
export const pendingThreads = ({ items, filter, tag, target }: { items: readonly ReviewItem[]; filter: ThreadFilter; tag: string | null; target: string | null }): ReviewItem[] => {
  if (filter === "closed" || tag !== null) return [];
  return items.filter((item) => item.thread === null && !isChoice(item) && (target === null || item.target === target));
};

/** 項目に向けたスレッドの件数（状態を問わない）と、レビュー中の新規スレッドの件数の和。返信と案の選択は数えない */
export const itemThreadCount = ({ threads, pending, id }: { threads: readonly Thread[]; pending: readonly ReviewItem[]; id: string }): number =>
  threads.filter((thread) => thread.target === id).length + pending.filter((item) => item.thread === null && !isChoice(item) && item.target === id).length;

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
  if (item.target === null) return "項目を指さないコメント";
  return isChoice(item) ? `${item.target} への案の選択` : `${item.target} へのコメント`;
};

/** 案の選択か（`choice` を持つ） */
export const isChoice = (item: ReviewItem): boolean => item.choice !== undefined && item.choice !== null;

/** レビュー中の書き込みのうち、その検討事項への案の選択（無ければ undefined） */
export const choiceOf = (items: readonly ReviewItem[], target: string): ReviewItem | undefined => items.find((item) => item.target === target && isChoice(item));

/** 利用者の未読の書き込み（`seen` が偽）を持つか。`seen` を持たない書き込みは未読にしない */
export const hasUnseen = (thread: Thread): boolean => thread.posts.some((post) => post.seen === false);

/** トップバーの未読の点（オープンのスレッドに利用者の未読があるか） */
export const anyOpenUnseen = (threads: readonly Thread[]): boolean => threads.some((thread) => thread.status === "open" && hasUnseen(thread));

/** 指したスレッドの書き込みを全て既読にした新しい並び（渡した並びは書き換えない） */
export const withSeen = ({ threads, id }: { threads: readonly Thread[]; id: string }): Thread[] =>
  threads.map((thread) => (thread.id === id ? { ...thread, posts: thread.posts.map((post) => ({ ...post, seen: true })) } : thread));
