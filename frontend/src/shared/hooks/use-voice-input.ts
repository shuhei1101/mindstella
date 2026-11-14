// 文字起こしの可否の query と、画面で 1 つの音声入力のうち入力欄の分をまとめて、部品へ渡す音声入力の props を返す
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { getGetTranscriptionQueryOptions, getRecords } from "@/shared/api/generated/preview";
import type { TranscriptionStatus } from "@/shared/api/generated/model";
import { micSupported, VOICE_TEXT } from "@/shared/core/voice";
import { commentsQuery, recordsQuery, threadsQuery } from "@/shared/hooks/preview-queries";
import { cancelVoice, finishVoice, startVoice, takeVoiceResult, useVoiceSessionFor, type VoiceAction, type VoiceDestination, type VoiceResult, type VoiceView } from "@/shared/stores/voice-store";

/** 音声入力の状態（部品設計の `voice`） */
export type VoicePhase = "idle" | "disabled" | "recording" | "transcribing";

/** 音声入力の結果（部品の `status` に重ねる） */
export type VoiceStatus = "idle" | "sent" | "inserted" | "reviewed" | "voice-failed";

export type VoiceInputOptions = {
  /** 入力欄の識別（`{target}#{loc}` か `thread:{id}` か `new-thread`） */
  key: string;
  destination: VoiceDestination;
  /** 入力欄を開く画面 */
  view: VoiceView;
  /** トップバーに出す入力欄の名前 */
  label: string;
  /** 入力欄の中身 */
  body: string;
  /** 入力欄の中身を書き換える */
  onBodyChange: (body: string) => void;
  /** ✓ を押したときのカーソルの位置 */
  getSelection: () => { start: number; end: number };
};

/** 文字起こしの可否の query のキー */
const transcriptionKey = () => getGetTranscriptionQueryOptions().queryKey;

/** 文字起こしの可否。マイクのボタンを描く画面と設定の画面が開いたときに読む（書き換えの知らせでは読み直さない） */
export const useTranscriptionStatus = () =>
  useQuery({
    ...getGetTranscriptionQueryOptions(),
    staleTime: Number.POSITIVE_INFINITY,
    select: (response) => (response.status === 200 ? response.data : null),
  });

/** 503 の結果から、使えない旨の可否を組む（知っている挙動とプリセットは残す） */
const unavailableStatus = (result: VoiceResult, known: TranscriptionStatus | null): TranscriptionStatus => ({
  presets: [],
  action: known?.action ?? "review",
  preset: known?.preset ?? null,
  available: false,
  reason: result.reason ?? "stopped",
  detail: result.detail,
});

const VOICE_ACTIONS = ["review", "send", "insert"] as const satisfies readonly VoiceAction[];

/** 記録の設定の、文字起こしの結果の扱い */
const transcriptionAction = (records: Awaited<ReturnType<typeof getRecords>> | undefined): VoiceAction | undefined => {
  const action = records?.status === 200 ? (records.data as { settings?: { transcription?: { action?: string } } }).settings?.transcription?.action : undefined;
  return VOICE_ACTIONS.find((one) => one === action);
};

type LocalResult = { key: string; status: VoiceStatus; detail: string | null; entered: boolean };

export const useVoiceInput = ({ key, destination, view, label, body, onBodyChange, getSelection }: VoiceInputOptions) => {
  const queryClient = useQueryClient();
  const status = useTranscriptionStatus();
  const records = useQuery(recordsQuery());
  const session = useVoiceSessionFor(key);
  const [result, setResult] = useState<LocalResult>({ key, status: "idle", detail: null, entered: false });
  // 画面に出ている入力欄の識別（外れたら null）。文字起こしを待つ間に外れたかを見る
  const shownKey = useRef<string | null>(null);

  /** 文字起こしを終えた結果を入力欄と `status` に当てる */
  const apply = useCallback(
    (owner: string, done: VoiceResult): void => {
      const show = (next: Omit<LocalResult, "key">): void => {
        setResult({ key: owner, ...next });
      };
      switch (done.kind) {
        case "reviewed":
          onBodyChange("");
          show({ status: "reviewed", detail: null, entered: false });
          void queryClient.invalidateQueries({ queryKey: commentsQuery().queryKey });
          return;
        case "sent":
          onBodyChange("");
          show({ status: "sent", detail: null, entered: done.entered });
          void queryClient.invalidateQueries({ queryKey: threadsQuery().queryKey });
          return;
        case "inserted":
          onBodyChange(done.body);
          show({ status: "inserted", detail: null, entered: false });
          return;
        case "failed":
          onBodyChange(done.body);
          show({ status: "voice-failed", detail: done.detail, entered: false });
          return;
        case "unavailable":
          // サービスが使えない: 可否を書き換えてマイクのボタンを押せなくする
          queryClient.setQueryData(transcriptionKey(), { status: 200, data: unavailableStatus(done, status.data ?? null), headers: new Headers() });
          show({ status: "voice-failed", detail: done.detail, entered: false });
          return;
        default: {
          const never: never = done.kind;
          return never;
        }
      }
    },
    [onBodyChange, queryClient, status.data],
  );

  // 入力欄が付いたとき、画面に無い間に終わった結果を受け取る
  const applyRef = useRef(apply);
  useEffect(() => {
    applyRef.current = apply;
  }, [apply]);
  useEffect(() => {
    shownKey.current = key;
    const away = takeVoiceResult(key);
    if (away !== null) applyRef.current(key, away);
    return () => {
      shownKey.current = null;
    };
  }, [key]);

  const mine = session !== null && session !== "busy" ? session : null;
  const availability = status.data ?? null;
  const blockedReason = !micSupported()
    ? VOICE_TEXT.noMicrophone
    : availability !== null && !availability.available
      ? availability.detail
      : session === "busy"
        ? VOICE_TEXT.busy
        : null;
  const voice: VoicePhase = blockedReason !== null ? "disabled" : (mine?.phase ?? "idle");

  const onVoiceStart = useCallback(async (): Promise<void> => {
    setResult({ key, status: "idle", detail: null, entered: false });
    const failure = await startVoice({ key, destination, view, label, selection: getSelection() });
    if (failure !== null) setResult({ key, status: "voice-failed", detail: failure === "denied" ? VOICE_TEXT.denied : VOICE_TEXT.noMicrophone, entered: false });
  }, [destination, getSelection, key, label, view]);

  const onVoiceCancel = useCallback(() => {
    if (mine !== null) cancelVoice();
  }, [mine]);

  const onVoiceDone = useCallback(async (): Promise<void> => {
    if (mine?.phase !== "recording") return;
    const { start, end } = getSelection();
    const done = await finishVoice({ body, start, end, action: transcriptionAction(records.data), mounted: () => shownKey.current === key });
    if (shownKey.current === key) apply(key, done);
  }, [apply, body, getSelection, key, mine, records.data]);

  const onVoiceBlocked = useCallback(() => {
    setResult({ key, status: "voice-failed", detail: blockedReason, entered: false });
    // マイクを使えるページなら、サービスが使えるようになったかを読み直す（録音は始めない）
    if (micSupported()) void queryClient.invalidateQueries({ queryKey: transcriptionKey() });
  }, [blockedReason, key, queryClient]);

  /** 音声入力の結果を消す（入力を始めたとき） */
  const clearResult = useCallback(() => {
    setResult((current) => (current.status === "idle" ? current : { key, status: "idle", detail: null, entered: false }));
  }, [key]);

  const shown = result.key === key ? result : null;
  return {
    voice,
    voiceReason: blockedReason,
    elapsed: mine?.elapsed ?? 0,
    levels: mine?.phase === "recording" ? mine.levels : [],
    status: shown?.status ?? "idle",
    detail: shown?.detail ?? null,
    entered: shown?.entered ?? false,
    onVoiceStart,
    onVoiceCancel,
    onVoiceDone,
    onVoiceBlocked,
    clearResult,
  };
};
