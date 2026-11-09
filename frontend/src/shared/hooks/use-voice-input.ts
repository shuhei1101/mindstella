// 文字起こしの可否の query と、コメント・返信の入力の録音・文字起こし・すぐ送るをまとめて、部品へ渡す音声入力の props を返す
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { getGetTranscriptionQueryOptions, getTranscription, postTranscription, sendNow } from "@/shared/api/generated/preview";
import type { TranscriptionStatus } from "@/shared/api/generated/model";
import { AppError } from "@/shared/core/app-error";
import type { Location } from "@/shared/core/records";
import { insertAtCursor, micSupported, startRecording, VOICE_TEXT, type Recording } from "@/shared/core/voice";
import { recordsQuery, threadsQuery } from "@/shared/hooks/preview-queries";

/** 音声入力の状態（部品設計の `voice`） */
export type VoicePhase = "idle" | "disabled" | "recording" | "transcribing";

/** 音声入力の結果（部品の `status` に重ねる） */
export type VoiceStatus = "idle" | "sent" | "inserted" | "voice-failed";

/** 向けた先（項目と箇所か、返信先のスレッド） */
export type VoiceDestination = { target: string | null; loc: Location | null } | { thread: string };

export type VoiceInputOptions = {
  destination: VoiceDestination;
  /** 入力欄の中身 */
  body: string;
  /** 入力欄の中身を書き換える */
  onBodyChange: (body: string) => void;
  /** ✓ を押したときのカーソルの位置 */
  getSelection: () => { start: number; end: number };
};

/** 録音は同時に 1 つ。録っている入力の印 */
let activeOwner: symbol | null = null;

/** 文字起こしの可否の query のキー */
const transcriptionKey = () => getGetTranscriptionQueryOptions().queryKey;

/** 文字起こしの可否。マイクのボタンを描く画面と設定の画面が開いたときに読む（書き換えの知らせでは読み直さない） */
export const useTranscriptionStatus = () =>
  useQuery({
    ...getGetTranscriptionQueryOptions(),
    staleTime: Number.POSITIVE_INFINITY,
    select: (response) => (response.status === 200 ? (response.data as TranscriptionStatus) : null),
  });

/** 向けた先を比べる文字列 */
const destinationKey = (destination: VoiceDestination): string => JSON.stringify(destination);

export const useVoiceInput = ({ destination, body, onBodyChange, getSelection }: VoiceInputOptions) => {
  const queryClient = useQueryClient();
  const status = useTranscriptionStatus();
  const records = useQuery(recordsQuery());
  const [phase, setPhase] = useState<"idle" | "recording" | "transcribing">("idle");
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<{ status: VoiceStatus; detail: string | null; entered: boolean }>({ status: "idle", detail: null, entered: false });
  const owner = useRef(Symbol("voice"));
  const recording = useRef<Recording | null>(null);
  // 録音を始めるたびに進める番号。結果が返ったとき、押したときの番号と違えば捨てる
  const ticket = useRef(0);
  const latest = useRef({ body, destination, onBodyChange, getSelection });
  latest.current = { body, destination, onBodyChange, getSelection };

  /** 録音を捨ててマイクを解放し、文字起こし中の結果も捨てる */
  const abandon = useCallback(() => {
    ticket.current += 1;
    recording.current?.cancel();
    recording.current = null;
    if (activeOwner === owner.current) activeOwner = null;
    setPhase("idle");
    setElapsed(0);
  }, []);

  // 向けた先が変わったら録音を捨てる（書き換えの知らせでの描き直しでは向けた先が変わらないので止めない）
  const currentKey = destinationKey(destination);
  const recordedKey = useRef(currentKey);
  useEffect(() => {
    if (recordedKey.current !== currentKey) {
      recordedKey.current = currentKey;
      abandon();
    }
  }, [currentKey, abandon]);
  // 使う部品が外れたら録音を捨てる
  useEffect(() => abandon, [abandon]);
  // 録音中は 1 秒ごとに経過の時間を進める
  useEffect(() => {
    if (phase !== "recording") return undefined;
    const timer = window.setInterval(() => {
      setElapsed((value) => value + 1);
    }, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [phase]);

  const availability = status.data ?? null;
  const blockedReason = !micSupported() ? VOICE_TEXT.noMicrophone : availability !== null && !availability.available ? availability.detail : null;
  const voice: VoicePhase = blockedReason !== null ? "disabled" : phase;

  const onVoiceStart = useCallback(async (): Promise<void> => {
    if (activeOwner !== null) return;
    activeOwner = owner.current;
    const mine = ticket.current + 1;
    ticket.current = mine;
    try {
      const started = await startRecording();
      // 待つ間に向けた先が変わった・外れた: 始めた録音を捨てる
      if (ticket.current !== mine) {
        started.cancel();
        return;
      }
      recording.current = started;
      setResult({ status: "idle", detail: null, entered: false });
      setElapsed(0);
      setPhase("recording");
    } catch (failure) {
      if (activeOwner === owner.current) activeOwner = null;
      if (ticket.current !== mine) return;
      setResult({ status: "voice-failed", detail: failure === "denied" ? VOICE_TEXT.denied : VOICE_TEXT.noMicrophone, entered: false });
    }
  }, []);

  const onVoiceCancel = useCallback(() => {
    abandon();
  }, [abandon]);

  const onVoiceDone = useCallback(async (): Promise<void> => {
    const current = recording.current;
    if (current === null) return;
    const mine = ticket.current;
    setPhase("transcribing");
    const { body: before, destination: target, onBodyChange: write, getSelection: selection } = latest.current;
    const { start, end } = selection();
    const finish = (next: { status: VoiceStatus; detail: string | null; entered: boolean }): void => {
      recording.current = null;
      if (activeOwner === owner.current) activeOwner = null;
      setPhase("idle");
      setResult(next);
    };
    const audio = await current.stop();
    let text: string;
    try {
      const response = await postTranscription(audio, { headers: { "Content-Type": audio.type } });
      text = (response.data as { text: string }).text;
    } catch (error) {
      if (ticket.current !== mine) return;
      // サービスが使えない: 可否を書き換えてマイクのボタンを押せなくする
      if (error instanceof AppError && error.statusCode === 503) {
        const reason = (error.body as { reason?: "stopped" | "unsupported" } | null)?.reason ?? "stopped";
        const known = status.data ?? null;
        const unavailable: TranscriptionStatus = {
          presets: [],
          action: known?.action ?? "send",
          preset: known?.preset ?? null,
          available: false,
          reason,
          detail: error.message,
        };
        queryClient.setQueryData(transcriptionKey(), { status: 200, data: unavailable, headers: new Headers() } as Awaited<ReturnType<typeof getTranscription>>);
        finish({ status: "voice-failed", detail: error.message, entered: false });
        return;
      }
      finish({ status: "voice-failed", detail: error instanceof AppError ? error.message : VOICE_TEXT.failed, entered: false });
      return;
    }
    if (ticket.current !== mine) return;
    // 話し声が無かった: 送信も挿入もしない
    if (text.trim() === "") {
      finish({ status: "voice-failed", detail: VOICE_TEXT.failed, entered: false });
      return;
    }
    const inserted = insertAtCursor(before, start, end, text);
    const settings = records.data?.status === 200 ? (records.data.data as { settings?: { transcription?: { action?: string } } }).settings : undefined;
    if (settings?.transcription?.action === "insert") {
      write(inserted.value);
      finish({ status: "inserted", detail: null, entered: false });
      return;
    }
    try {
      const sent = await sendNow({ ...target, body: inserted.value });
      if (ticket.current !== mine) return;
      write("");
      finish({ status: "sent", detail: null, entered: (sent.data as { entered?: boolean }).entered === true });
      await queryClient.invalidateQueries({ queryKey: threadsQuery().queryKey });
    } catch {
      if (ticket.current !== mine) return;
      write(inserted.value);
      finish({ status: "voice-failed", detail: VOICE_TEXT.sendFailed, entered: false });
    }
  }, [queryClient, records.data, status.data]);

  const onVoiceBlocked = useCallback(() => {
    setResult({ status: "voice-failed", detail: blockedReason, entered: false });
    // マイクを使えるページなら、サービスが使えるようになったかを読み直す（録音は始めない）
    if (micSupported()) void queryClient.invalidateQueries({ queryKey: transcriptionKey() });
  }, [blockedReason, queryClient]);

  /** 音声入力の結果を消す（入力を始めたとき） */
  const clearResult = useCallback(() => {
    setResult((current) => (current.status === "idle" ? current : { status: "idle", detail: null, entered: false }));
  }, []);

  return {
    voice,
    voiceReason: blockedReason,
    elapsed,
    status: result.status,
    detail: result.detail,
    entered: result.entered,
    onVoiceStart,
    onVoiceCancel,
    onVoiceDone,
    onVoiceBlocked,
    clearResult,
  };
};
