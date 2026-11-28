// レビュー中の書き込みを溜める・書き換える・消す・まとめて送る mutation と、下書きの保存
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { addComment, removeComment, saveDraft, sendComments, updateComment } from "@/shared/api/generated/preview";
import type { CommentInput, DraftInput, RemovedComment, SendReply } from "@/shared/api/generated/model";
import { commentsQuery, threadsQuery } from "@/shared/hooks/preview-queries";
import { SESSION_QUERY_KEY } from "@/shared/hooks/use-session-status";
import { discardReviewVoice } from "@/shared/stores/voice-store";

/** 入力が止まってから下書きを保存するまでのミリ秒 */
const DRAFT_SAVE_DELAY_MS = 500;

/** 下書きの向けた先のキー（項目・箇所・スレッドの組） */
const draftKey = ({ target, loc, thread }: Pick<DraftInput, "target" | "loc" | "thread">): string => JSON.stringify([target ?? null, loc ?? null, thread ?? null]);

/** 向けた先ごとの、予約した下書きの保存 */
const draftTimers = new Map<string, number>();

/** 下書きを送る。保てなかったときは画面に出さない（入力欄の中身は残り、次の入力か溜めたときに送り直す） */
const sendDraft = (draft: DraftInput): void => {
  saveDraft(draft).catch(() => undefined);
};

/** 予約した下書きの保存を取り消す */
const cancelDraft = (key: string): void => {
  window.clearTimeout(draftTimers.get(key));
  draftTimers.delete(key);
};

/** 書き込みを溜め、レビュー中の書き込みを読み直す。溜めた向けた先の予約した下書きの保存は取り消す（サーバーがその下書きを消すため。案の選択は下書きを消さない） */
export const useAddComment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CommentInput) => {
      if (input.choice === undefined) cancelDraft(draftKey(input));
      return (await addComment(input)).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey }),
  });
};

/** 書き込みの本文か案の選択の記号を書き換えるか箇所を外し、読み直す（案の選択の一言は null で削除する） */
export const useUpdateComment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: { id: string; body?: string | null; loc?: null; choice?: { key: string } }) => (await updateComment(id, patch)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey }),
  });
};

/** 書き込みを消し、「元に戻す」のために消した中身を返す。その書き込みの修正の入力の録音と結果は、読み直しを待たずに捨てる */
export const useRemoveComment = () => {
  const queryClient = useQueryClient();
  return useMutation<RemovedComment, Error, string>({
    mutationFn: async (id) => (await removeComment(id)).data as RemovedComment,
    onSuccess: (_removed, id) => {
      discardReviewVoice([id]);
      return queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey });
    },
  });
};

/** チェックした書き込みをまとめて送り、送った書き込みの修正の入力の録音と結果を捨てて、レビュー中の書き込みとスレッドを読み直す。409 の `stale` は AppError の `body` で受ける */
export const useSendComments = () => {
  const queryClient = useQueryClient();
  return useMutation<SendReply, Error, string[]>({
    mutationFn: async (ids) => (await sendComments({ ids })).data as SendReply,
    onSuccess: async (_reply, ids) => {
      discardReviewVoice(ids);
      // 送信の後は MindStella のセッションの状態も取得し直す（再起動の途中に送ったコメントの件数）
      await Promise.all([queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey }), queryClient.invalidateQueries({ queryKey: threadsQuery().queryKey }), queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY })]);
    },
  });
};

/** 下書きの保存を予約する関数（入力が止まって 500ms 後に `PUT /api/drafts`。向けた先ごとに待ちを分ける）。入力欄を離れたときは `now` を真にしてすぐ送る */
export const useSaveDraft = () =>
  useCallback((draft: DraftInput, now = false) => {
    const key = draftKey(draft);
    cancelDraft(key);
    if (now) {
      sendDraft(draft);
      return;
    }
    draftTimers.set(
      key,
      window.setTimeout(() => {
        draftTimers.delete(key);
        sendDraft(draft);
      }, DRAFT_SAVE_DELAY_MS),
    );
  }, []);
