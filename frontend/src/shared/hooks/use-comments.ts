// レビュー中の書き込みを溜める・書き換える・消す・まとめて送る mutation と、書きかけの保存
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { addComment, removeComment, saveDraft, sendComments, updateComment } from "@/shared/api/generated/preview";
import type { CommentInput, DraftInput, RemovedComment, SendReply } from "@/shared/api/generated/model";
import { commentsQuery, threadsQuery } from "@/shared/hooks/preview-queries";

/** 入力が止まってから書きかけを保存するまでのミリ秒（今の画面の `DRAFT_SAVE_DELAY_MS` と同じ） */
const DRAFT_SAVE_DELAY_MS = 500;

/** 書きかけの向けた先のキー（項目・箇所・スレッドの組） */
const draftKey = ({ target, loc, thread }: Pick<DraftInput, "target" | "loc" | "thread">): string => JSON.stringify([target ?? null, loc ?? null, thread ?? null]);

/** 向けた先ごとの、予約した書きかけの保存 */
const draftTimers = new Map<string, number>();

/** 書きかけを送る。保てなかったときは画面に出さない（今の画面と同じ。入力欄の中身は残り、次の入力か溜めたときに送り直す） */
const sendDraft = (draft: DraftInput): void => {
  saveDraft(draft).catch(() => undefined);
};

/** 予約した書きかけの保存を取り消す */
const cancelDraft = (key: string): void => {
  window.clearTimeout(draftTimers.get(key));
  draftTimers.delete(key);
};

/** 書き込みを溜め、レビュー中の書き込みを読み直す。溜めた向けた先の予約した書きかけの保存は取り消す（サーバーがその書きかけを消すため） */
export const useAddComment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CommentInput) => {
      cancelDraft(draftKey(input));
      return (await addComment(input)).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey }),
  });
};

/** 書き込みの本文を書き換えるか箇所を外し、読み直す */
export const useUpdateComment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: { id: string; body?: string; loc?: null }) => (await updateComment(id, patch)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey }),
  });
};

/** 書き込みを消し、「元に戻す」のために消した中身を返す */
export const useRemoveComment = () => {
  const queryClient = useQueryClient();
  return useMutation<RemovedComment, Error, string>({
    mutationFn: async (id) => (await removeComment(id)).data as RemovedComment,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey }),
  });
};

/** チェックした書き込みをまとめて送り、レビュー中の書き込みとスレッドを読み直す。409 の `stale` は AppError の `body` で受ける */
export const useSendComments = () => {
  const queryClient = useQueryClient();
  return useMutation<SendReply, Error, string[]>({
    mutationFn: async (ids) => (await sendComments({ ids })).data as SendReply,
    onSuccess: async () => {
      await Promise.all([queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey }), queryClient.invalidateQueries({ queryKey: threadsQuery().queryKey })]);
    },
  });
};

/** 書きかけの保存を予約する関数（入力が止まって 500ms 後に `PUT /api/drafts`。向けた先ごとに待ちを分ける）。入力欄を離れたときは `now` を真にしてすぐ送る */
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
