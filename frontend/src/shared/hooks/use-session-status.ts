// 画面の MindStella のセッションの状態の query と、画面からの再起動の mutation をまとめ、状態のバーへ指定する状態を返す
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getGetSessionQueryOptions, postSessionRestart } from "@/shared/api/generated/preview";
import type { SessionStatusReply } from "@/shared/api/generated/model";
import type { SessionStatus } from "@/shared/components/session-status-banner";
import { AppError } from "@/shared/core/app-error";
import { isEmbedded } from "@/shared/core/embedded";

/** 書き換えの通知の `session` とまとめて送信の成功が再読み込みする query のキー */
export const SESSION_QUERY_KEY = ["session"] as const;

/** 記録が無い警告の値（インターフェース定義『画面の MindStella のセッションの状態』の `warnings`） */
const LAUNCH_RECORD_MISSING = "launch_record_missing";

/** 再起動の途中で断られた 409（`stage: restarting`）か。ほかの段階の 409 と失敗は理由を出す */
const isRestartingConflict = (error: AppError): boolean =>
  error.statusCode === 409 && typeof error.body === "object" && error.body !== null && (error.body as { stage?: unknown }).stage === "restarting";

/** 応答から状態のバーの状態を組み立てる（部品設計『トップバー.tsx』の `sessionStatus` の対応） */
export const toSessionStatus = (response: SessionStatusReply, retrying: boolean, warningClosed: boolean): SessionStatus => {
  if (response.status === "restarting") return { kind: "restarting", waiting: response.waiting };
  // 落ちていて理由がある: 再起動の失敗として出す（理由が無いときは次の送信で再起動するので出さない）
  if (response.status !== "running" && response.status !== "none" && response.last_error !== null) {
    return { kind: "failed", reason: response.last_error, retrying };
  }
  if (response.warnings.includes(LAUNCH_RECORD_MISSING) && !warningClosed) return { kind: "launch_record_missing" };
  return { kind: "running" };
};

/** 状態のバーへ指定する状態と、再起動・警告を閉じる操作を返す。配る書き出しでは取得せず running を返す */
export const useSessionStatus = (): { status: SessionStatus; restart: () => void; closeWarning: () => void } => {
  const queryClient = useQueryClient();
  const embedded = isEmbedded();
  const query = useQuery({
    ...getGetSessionQueryOptions(),
    queryKey: SESSION_QUERY_KEY,
    enabled: !embedded,
    select: (response) => (response.status === 200 ? response.data : null),
  });
  const restart = useMutation({
    mutationFn: () => postSessionRestart(),
    // 受け付けた後も、再起動の途中で断られた後も、今の状態を取得し直す
    onSettled: () => queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY }),
  });
  // 記録が無い警告を閉じた（再起動の途中になったら戻し、再起動の後の警告は再び出す）
  const [warningClosed, setWarningClosed] = useState(false);
  const data = query.data ?? null;
  if (warningClosed && data?.status === "restarting") setWarningClosed(false);
  const base: SessionStatus = data === null ? { kind: "running" } : toSessionStatus(data, restart.isPending, warningClosed);
  // 再起動の依頼が再起動の途中以外の理由で断られた: その理由を出し、「再起動」を押せるままにする
  const refused = restart.error instanceof AppError && !isRestartingConflict(restart.error) ? restart.error.message : null;
  const status: SessionStatus = base.kind === "failed" && refused !== null ? { ...base, reason: refused } : base;
  return {
    status,
    restart: () => {
      restart.mutate();
    },
    closeWarning: () => {
      setWarningClosed(true);
    },
  };
};
