// 本文の中のスレッドの ID（`TH-150`）と書き込みの ID（`TH-150-2`）を、記録にあるスレッドと書き込みに結ぶ

/** スレッドの ID から引いたタイトルと書き込みの ID の並び（記録に無ければ null） */
export type LookupThread = (threadId: string) => { title: string; posts: readonly string[] } | null;

/** 押したスレッド（書き込みの ID のときはその ID。スレッドの ID のときは null） */
export type OpenThread = (threadId: string, postId: string | null) => void;

/** ID を、記録にあるスレッドと書き込みの組に分ける（記録に無いスレッド・スレッドに無い書き込みは null） */
export const resolveThreadId = (id: string, threads: LookupThread): { threadId: string; postId: string | null } | null => {
  const [, number, post] = /^TH-(\d+)(?:-(\d+))?$/.exec(id) ?? [];
  if (number === undefined) return null;
  const threadId = `TH-${number}`;
  const thread = threads(threadId);
  if (thread === null) return null;
  if (post === undefined) return { threadId, postId: null };
  return thread.posts.includes(id) ? { threadId, postId: id } : null;
};
