// 本文の中のスレッドの ID（`TH-150`）と書き込みの ID（`TH-150-2`）を、記録にあるスレッドと書き込みに結ぶ

/** スレッドの ID から引いたタイトルと書き込みの ID の並び（記録に無ければ null） */
export type LookupThread = (threadId: string) => { title: string; posts: readonly string[]; status?: "open" | "closed" } | null;

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

/** スレッドの並びから、スレッドの ID → タイトルと書き込みの ID の並びを引く関数を作る */
export const threadLookupOf = (threads: readonly { id: string; summary: string | null; status: "open" | "closed"; posts: readonly { id: string }[] }[]): LookupThread => {
  const byId = new Map(threads.map((thread) => [thread.id, { title: thread.summary ?? thread.id, status: thread.status, posts: thread.posts.map((post) => post.id) }]));
  return (threadId) => byId.get(threadId) ?? null;
};

/** 書き込みの ID のリンクで開こうとしている書き込み（スレッドの画面が開いた直後に最新の書き込みへ移すかを決める） */
let requestedPost: string | null = null;

/** 書き込みの ID のリンクで開く書き込みを控える */
export const requestPost = (postId: string): void => {
  requestedPost = postId;
};

/** スレッドの画面が開いたときに、そのスレッドの書き込みを指して開いたかを取り出す（取り出したら控えを消す） */
export const takeRequestedPost = (threadId: string): string | null => {
  const postId = requestedPost;
  requestedPost = null;
  return postId?.startsWith(`${threadId}-`) === true ? postId : null;
};

/** 開いたスレッドの画面で、書き込みの要素（`data-post-id`）が描かれるのを待ってスクロールし、フォーカスを移す（描かれなければ何もしない） */
export const revealPost = (postId: string, frames = 60): void => {
  const element = document.querySelector<HTMLElement>(`[data-post-id="${CSS.escape(postId)}"]`);
  if (element !== null) {
    element.scrollIntoView({ block: "nearest" });
    element.focus({ preventScroll: true });
    return;
  }
  if (frames > 0) requestAnimationFrame(() => { revealPost(postId, frames - 1); });
};
