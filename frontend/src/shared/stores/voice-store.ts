// 画面で 1 つの音声入力。録音を始めた入力欄の部品が外れても、録音と文字起こしを続ける
import { create } from "zustand";

import { addComment, postTranscription, saveDraft, sendNow } from "@/shared/api/generated/preview";
import { AppError } from "@/shared/core/app-error";
import type { Location } from "@/shared/core/records";
import { acquireWakeLock, insertAtCursor, pushLevel, RecordingError, startRecording, VOICE_TEXT, type Recording, type RecordingFailure } from "@/shared/core/voice";

/** 向けた先（項目と箇所か、返信先のスレッド） */
export type VoiceDestination = { target: string | null; loc: Location | null } | { thread: string };

/** 入力欄を開く画面 */
export type VoiceView = "panel" | "full" | "comments" | "thread";

/** 録音を始めた入力欄 */
export type VoiceInput = {
  /** 入力欄の識別 */
  key: string;
  destination: VoiceDestination;
  view: VoiceView;
  /** トップバーに出す入力欄の名前 */
  label: string;
  /** マイクを押したときの選んだ範囲 */
  selection: { start: number; end: number };
};

/** いま録音・文字起こししている入力欄 */
export type VoiceSession = VoiceInput & {
  phase: "recording" | "transcribing";
  /** 経過の秒数 */
  elapsed: number;
  levels: number[];
  /** 録音を始めるたびに 1 進める番号 */
  ticket: number;
};

/** 文字起こしを終えた結果。`body` は入力欄に残す中身、`caret` は挿入した文字の後ろの位置（`inserted` だけ）、`count` は溜めた後のレビュー中の件数（`reviewed` だけ）、`entered` は Claude Code へ入力したか（`sent` だけ）、`reason` は使えない理由（`unavailable` だけ） */
export type VoiceResult = {
  kind: "reviewed" | "sent" | "inserted" | "failed" | "unavailable";
  body: string;
  caret: number | null;
  count: number | null;
  entered: boolean;
  detail: string | null;
  reason: "stopped" | "unsupported" | null;
};

/** 結果の既定の値に `kind` と変わる値を重ねる */
const resultOf = (kind: VoiceResult["kind"], body: string, patch: Partial<VoiceResult> = {}): VoiceResult => ({ kind, body, caret: null, count: null, entered: false, detail: null, reason: null, ...patch });

/** トップバーの下の音声入力の知らせ */
export type VoiceNotice = { kind: "discarded" | "failed"; text: string; key: string | null };

/** 文字起こしの結果の扱い */
export type VoiceAction = "review" | "send" | "insert";

/** ✓ を押したときの入力欄 */
export type VoiceFinishInput = {
  body: string;
  start: number;
  end: number;
  action: VoiceAction | undefined;
  /** 入力欄がまだ画面にあるか */
  mounted: () => boolean;
};

type VoiceState = {
  session: VoiceSession | null;
  notice: VoiceNotice | null;
  /** 入力欄が画面に無い間に終わった結果 */
  results: Record<string, VoiceResult>;
};

const useVoiceStore = create<VoiceState>()(() => ({ session: null, notice: null, results: {} }));

/** 録音中の 1 回分（`session` が `recording` の間だけ持つ） */
let recording: Recording | null = null;
/** 画面の消灯の抑止を解く関数（抑止していなければ null） */
let releaseWakeLock: (() => void) | null = null;
/** 経過の時間を進めるタイマー */
let timer: number | null = null;
/** 録音を始めている途中か（許可を待つ間に 2 つ目を始めない） */
let starting = false;
/** 最後に発行した番号 */
let lastTicket = 0;
/** 録音を始めた入力欄の向けた先と開く画面（知らせの「入力欄を開く」で開く） */
const targets = new Map<string, Pick<VoiceInput, "destination" | "view">>();

/** 今の番号の録音中の session があるか */
const isRecording = (ticket: number): boolean => {
  const { session } = useVoiceStore.getState();
  return session?.ticket === ticket && session.phase === "recording";
};

/** 画面の消灯の抑止を求める。待つ間に録音が終わった・もう抑止していたら解く */
const lock = async (ticket: number): Promise<void> => {
  const release = await acquireWakeLock();
  if (!isRecording(ticket) || releaseWakeLock !== null) {
    release();
    return;
  }
  releaseWakeLock = release;
};

/** 画面の消灯の抑止を解く */
const unlock = (): void => {
  releaseWakeLock?.();
  releaseWakeLock = null;
};

/** 経過の時間のタイマーを止める */
const stopTimer = (): void => {
  if (timer !== null) window.clearInterval(timer);
  timer = null;
};

/** 録音を捨てて、session を空にする */
const abandon = (): void => {
  recording?.cancel();
  recording = null;
  stopTimer();
  unlock();
  useVoiceStore.setState({ session: null });
};

// 画面が見えたとき、録音中なら抑止を求め直す（ブラウザは画面が隠れると抑止を解く）
document.addEventListener("visibilitychange", () => {
  const { session } = useVoiceStore.getState();
  if (document.visibilityState !== "visible" || session?.phase !== "recording") return;
  releaseWakeLock = null;
  void lock(session.ticket);
});

/** いまの音声入力 */
export const useVoiceSession = (): VoiceSession | null => useVoiceStore((state) => state.session);

/** 入力欄の分だけの音声入力（ほかの入力欄の音声入力中は `busy`） */
export const useVoiceSessionFor = (key: string): VoiceSession | "busy" | null =>
  useVoiceStore((state) => (state.session === null ? null : state.session.key === key ? state.session : "busy"));

/** トップバーの下の知らせ */
export const useVoiceNotice = (): VoiceNotice | null => useVoiceStore((state) => state.notice);

/** 入力欄が画面に無い間に終わった結果 */
export const useVoiceResult = (key: string): VoiceResult | null => useVoiceStore((state) => state.results[key] ?? null);

/** session が無いときだけ録音を始め、画面の消灯の抑止を求める。始められなかった理由を返す */
export const startVoice = async (input: VoiceInput): Promise<RecordingFailure | null> => {
  if (useVoiceStore.getState().session !== null || starting) return null;
  starting = true;
  lastTicket += 1;
  const ticket = lastTicket;
  try {
    recording = await startRecording((level) => {
      const { session } = useVoiceStore.getState();
      if (session?.ticket === ticket) useVoiceStore.setState({ session: { ...session, levels: pushLevel(session.levels, level) } });
    });
  } catch (failure) {
    if (failure instanceof RecordingError) return failure.reason;
    throw failure;
  } finally {
    starting = false;
  }
  targets.set(input.key, { destination: input.destination, view: input.view });
  useVoiceStore.setState({ session: { ...input, phase: "recording", elapsed: 0, levels: [], ticket } });
  timer = window.setInterval(() => {
    const { session } = useVoiceStore.getState();
    if (session !== null && isRecording(ticket)) useVoiceStore.setState({ session: { ...session, elapsed: session.elapsed + 1 } });
  }, 1000);
  await lock(ticket);
  return null;
};

/** 録音を捨てて抑止を解く（× を押したとき） */
export const cancelVoice = (): void => {
  abandon();
};

/** 挿入した中身を設定の挙動で溜める・送る */
const deliver = async (destination: VoiceDestination, inserted: { value: string; caret: number }, action: VoiceAction): Promise<VoiceResult> => {
  const payload = { ...destination, body: inserted.value };
  switch (action) {
    case "insert":
      return resultOf("inserted", inserted.value, { caret: inserted.caret });
    case "send":
      try {
        const sent = await sendNow(payload);
        return resultOf("sent", "", { entered: (sent.data as { entered?: boolean }).entered === true });
      } catch {
        // 送れなかった: 挿入した中身を入力欄に残す
        return resultOf("failed", inserted.value, { detail: VOICE_TEXT.sendFailed });
      }
    case "review":
      try {
        const added = await addComment(payload);
        return resultOf("reviewed", "", { count: (added.data as { count?: number }).count ?? null });
      } catch {
        // 溜められなかった: 挿入した中身を入力欄に残す
        return resultOf("failed", inserted.value, { detail: VOICE_TEXT.reviewFailed });
      }
    default: {
      const never: never = action;
      return never;
    }
  }
};

/** 失敗した段（入力欄が画面に無い間の知らせの文を選ぶ） */
type VoiceStage = "transcribe" | VoiceAction;

/** 録った音声を文字起こしし、挿入して設定の挙動で溜める・送る */
const transcribeAndDeliver = async (audio: Blob, destination: VoiceDestination, input: VoiceFinishInput): Promise<{ result: VoiceResult; stage: VoiceStage }> => {
  let text: string;
  try {
    const response = await postTranscription(audio, { headers: { "Content-Type": audio.type } });
    text = (response.data as { text: string }).text;
  } catch (error) {
    if (error instanceof AppError && error.statusCode === 503) {
      const reason = (error.body as { reason?: "stopped" | "unsupported" } | null)?.reason ?? "stopped";
      return { result: resultOf("unavailable", input.body, { reason, detail: error.message }), stage: "transcribe" };
    }
    return { result: resultOf("failed", input.body, { detail: error instanceof AppError ? error.message : VOICE_TEXT.failed }), stage: "transcribe" };
  }
  // 話し声が無かった: 溜めも送りもしない
  if (text.trim() === "") return { result: resultOf("failed", input.body, { detail: VOICE_TEXT.failed }), stage: "transcribe" };
  const action = input.action ?? "review";
  return { result: await deliver(destination, insertAtCursor(input.body, input.start, input.end, text), action), stage: action };
};

/** 入力欄が画面に無い間に失敗したときの知らせの文 */
const awayText = (stage: VoiceStage, label: string): string =>
  stage === "review" ? VOICE_TEXT.awayReviewFailed(label) : stage === "send" ? VOICE_TEXT.awaySendFailed(label) : VOICE_TEXT.awayTranscribeFailed(label);

/** 文字起こしを終える。入力欄が画面に無い間に終わったら書きかけへ当て、失敗だけを知らせる */
export const finishVoice = async (input: VoiceFinishInput): Promise<VoiceResult> => {
  const { session } = useVoiceStore.getState();
  const current = recording;
  if (session === null || session.phase !== "recording" || current === null) return resultOf("failed", input.body, { detail: VOICE_TEXT.failed });
  recording = null;
  stopTimer();
  unlock();
  useVoiceStore.setState({ session: { ...session, phase: "transcribing" } });
  const audio = await current.stop();
  const { result, stage } = await transcribeAndDeliver(audio, session.destination, input);
  if (useVoiceStore.getState().session?.ticket === session.ticket) useVoiceStore.setState({ session: null });
  if (input.mounted()) return result;
  if (result.kind !== "unavailable") await saveDraft({ ...session.destination, body: result.body });
  useVoiceStore.setState((state) => ({
    results: { ...state.results, [session.key]: result },
    notice: result.kind === "failed" || result.kind === "unavailable" ? { kind: "failed", text: awayText(stage, session.label), key: session.key } : state.notice,
  }));
  return result;
};

/** 向けた先の ID（知らせに出す） */
const destinationId = (destination: VoiceDestination): string => ("thread" in destination ? destination.thread : (destination.target ?? ""));

/** 記録を読み直したとき、向けた先の項目・スレッドが無ければ録音を捨てて知らせる */
export const discardVoice = (exists: (destination: VoiceDestination) => boolean): void => {
  const { session } = useVoiceStore.getState();
  if (session === null || exists(session.destination)) return;
  abandon();
  useVoiceStore.setState({ notice: { kind: "discarded", text: VOICE_TEXT.discarded(destinationId(session.destination)), key: null } });
};

/** 入力欄の向けた先と開く画面（録音を始めていない入力欄は null） */
export const voiceTargetOf = (key: string): Pick<VoiceInput, "destination" | "view"> | null => targets.get(key) ?? null;

/** 知らせを閉じる */
export const dismissVoiceNotice = (): void => {
  useVoiceStore.setState({ notice: null });
};

/** 入力欄が画面に無い間の結果を受け取って消す */
export const takeVoiceResult = (key: string): VoiceResult | null => {
  const result = useVoiceStore.getState().results[key];
  if (result === undefined) return null;
  useVoiceStore.setState((state) => ({ results: Object.fromEntries(Object.entries(state.results).filter(([name]) => name !== key)) }));
  return result;
};

/** 今の状態（テストと React の外から読む） */
export const readVoiceState = (): VoiceState => useVoiceStore.getState();

/** 録音を捨てて初めの状態に戻す（テスト） */
export const resetVoiceStore = (): void => {
  abandon();
  starting = false;
  targets.clear();
  useVoiceStore.setState({ session: null, notice: null, results: {} });
};
