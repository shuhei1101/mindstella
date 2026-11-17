// 書き換えの知らせ（インターフェース定義『書き換えの知らせ』）へつなぎ、記録の query を読み直す
import type { QueryClient } from "@tanstack/react-query";

import { getComments, getRecords, getThreads } from "@/shared/api/generated/preview";
import { AppError } from "@/shared/core/app-error";
import type { ReviewItem, Thread } from "@/shared/core/comments";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { voiceDestinationExists } from "@/shared/core/voice";
import { invalidatePreview } from "@/shared/hooks/preview-queries";
import { useConnectionStore } from "@/shared/stores/connection-store";
import { useDuplicateIdsStore } from "@/shared/stores/duplicate-ids-store";
import { releaseRefresh, requestRefresh, useRefreshHoldStore, watchTextFocus } from "@/shared/stores/refresh-hold-store";
import { discardVoice, readVoiceState, subscribeVoice } from "@/shared/stores/voice-store";

/** 書き換えの知らせのパス */
export const EVENTS_URL = "/api/events";

/** 音声入力の間に書き換えを受けたとき、記録・スレッド・レビュー中のコメントを query のキャッシュに入れずに読み、録音の行き先が無ければ録音を捨てる */
export const checkVoiceDestination = async (): Promise<void> => {
  if (readVoiceState().session === null) return;
  let responses;
  try {
    responses = await Promise.all([getRecords(), getThreads(), getComments()]);
  } catch (error) {
    // 読めなければ何もしない（次の書き換えか、保留の解除の読み直しで確かめる）
    if (error instanceof AppError) return;
    throw error;
  }
  const [records, threads, comments] = responses;
  if (records.status !== 200 || threads.status !== 200 || comments.status !== 200) return;
  const index = buildIndex(records.data as unknown as MindmapData);
  const threadIds = new Set([
    ...(threads.data.threads as unknown as Thread[]).map((thread) => thread.id),
    ...((comments.data.items as unknown as ReviewItem[] | undefined) ?? []).map((item) => item.id),
  ]);
  discardVoice(voiceDestinationExists({ itemIds: new Set(index.byId.keys()), threadIds }));
};

/** `duplicate_ids` の `data`（ID の JSON の配列）を読む。読めなければ null */
const parseDuplicateIds = (data: unknown): string[] | null => {
  if (typeof data !== "string") return null;
  try {
    const value: unknown = JSON.parse(data);
    return Array.isArray(value) && value.every((entry) => typeof entry === "string") ? value : null;
  } catch {
    return null;
  }
};

/** `EVENTS_URL` へつなぎ、`changed` とつなぎ直しで記録の query の読み直しを反映の依頼に渡し（入力中・音声入力中は保留して離れたときに読み直す）、`duplicate_ids` で重なった ID を、接続の状態を書き換える。つなぎ直しは EventSource に任せ、閉じる関数を返す */
export const connectEvents = (queryClient: QueryClient): (() => void) => {
  const source = new EventSource(EVENTS_URL);
  const { setConnection } = useConnectionStore.getState();
  const refresh = (): void => {
    void invalidatePreview(queryClient);
  };
  const stopWatching = watchTextFocus(document);
  // フォーカスが離れたとき・音声入力が終わったときに、保留していた読み直しを 1 回だけ行う
  const release = (): void => {
    releaseRefresh(refresh);
  };
  const unsubscribeHold = useRefreshHoldStore.subscribe(release);
  const unsubscribeVoice = subscribeVoice(release);
  source.addEventListener("open", () => {
    setConnection("online");
    // 切れている間の書き換えを拾う
    requestRefresh(refresh);
  });
  source.addEventListener("changed", () => {
    requestRefresh(refresh);
    // 音声入力の間は画面に反映せず、録音の行き先の有無だけを確かめる
    if (readVoiceState().session !== null) void checkVoiceDestination();
  });
  source.addEventListener("duplicate_ids", (event) => {
    const ids = parseDuplicateIds((event as MessageEvent<unknown>).data);
    // 読めない知らせは捨てる（次の知らせで描き直す）
    if (ids !== null) useDuplicateIdsStore.getState().setIds(ids);
  });
  source.addEventListener("error", () => {
    // 前に読んだ記録の query は残し、トップバーに切れたことを出す
    setConnection("offline");
  });
  return () => {
    source.close();
    stopWatching();
    unsubscribeHold();
    unsubscribeVoice();
  };
};
