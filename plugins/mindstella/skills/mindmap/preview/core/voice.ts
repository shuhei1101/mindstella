// コメント・返信の入力の録音（マイクを使えるか・録音の開始と止め方）・カーソルの位置への挿入・文字起こしの結果の組み立て。

namespace MindmapPreview {
  /** `MediaRecorder.isTypeSupported` が真の最初の形で録る（どれも偽ならブラウザの既定） */
  export const VOICE_MIME_TYPES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"] as const;

  /** サーバーが返さない理由の文 */
  export const VOICE_TEXT = {
    noMicrophone: "このページではマイクを使用できません。HTTPS か localhost の URL で開いてください。",
    denied: "マイクを使用できませんでした。ブラウザの設定でこのページのマイクを許可してください。",
    failed: "文字起こしできませんでした。もう一度お試しください。",
    sendFailed: "送信できませんでした。文字起こしの結果は入力欄に残しています。",
  } as const;

  /** 録音中の 1 回分。`stop` と `cancel` のどちらかを 1 回だけ呼ぶ */
  export type Recording = {
    /** 録音を止め、マイクのトラックを全て止めて、録った音声を返す */
    stop: () => Promise<Blob>;
    /** 録音を止めて捨て、マイクのトラックを全て止める */
    cancel: () => void;
  };

  /** 録音を始められなかった理由（許可の拒否 / それ以外） */
  export type RecordingFailure = "denied" | "no-microphone";

  /** 文字起こしの結果 */
  export type VoiceOutcome = {
    kind: "sent" | "inserted" | "failed" | "unavailable";
    /** 入力欄に置く中身 */
    body: string;
    /** 置くカーソルの位置（挿入した文字の後ろ。動かさないときは null） */
    caret: number | null;
    /** `sent` のとき、Claude Code へ入力したか */
    entered: boolean;
    /** `failed`・`unavailable` の理由の文 */
    detail: string | null;
    /** `unavailable` の理由 */
    reason: "stopped" | "unsupported" | null;
  };

  /** 録音の機能を持つ窓（テストでは偽のものを渡す） */
  type MediaWindow = {
    navigator: { mediaDevices?: { getUserMedia?: (constraints: MediaStreamConstraints) => Promise<MediaStream> } };
    MediaRecorder?: typeof MediaRecorder;
  };

  /** ブラウザが getUserMedia と MediaRecorder を持つかを返す（HTTPS でも localhost でもない経路では持たない） */
  export function micSupported(win: MediaWindow = window): boolean {
    return typeof win.navigator.mediaDevices?.getUserMedia === "function" && typeof win.MediaRecorder === "function";
  }

  /** マイクの許可を得て録音を始め、録音を返す。許可が得られなければ理由で断る */
  export async function startRecording(win: MediaWindow = window): Promise<Recording> {
    const getUserMedia = win.navigator.mediaDevices?.getUserMedia;
    const Recorder = win.MediaRecorder;
    if (getUserMedia === undefined || Recorder === undefined) throw "no-microphone" satisfies RecordingFailure;
    let stream: MediaStream;
    try {
      stream = await getUserMedia.call(win.navigator.mediaDevices, { audio: true });
    } catch (error) {
      // 許可を拒否した: 許可が要る旨を出す。それ以外（マイクが無いなど）は使えない旨を出す
      const name = error instanceof DOMException ? error.name : "";
      throw (name === "NotAllowedError" || name === "SecurityError" ? "denied" : "no-microphone") satisfies RecordingFailure;
    }
    const mimeType = VOICE_MIME_TYPES.find((type) => Recorder.isTypeSupported(type));
    const recorder = new Recorder(stream, mimeType === undefined ? undefined : { mimeType });
    const chunks: Blob[] = [];
    let keep = true;
    recorder.addEventListener("dataavailable", (event: BlobEvent) => {
      if (keep) chunks.push(event.data);
    });
    const release = (): void => {
      for (const track of stream.getTracks()) track.stop();
    };
    recorder.start();
    return {
      stop: () =>
        new Promise<Blob>((resolve) => {
          recorder.addEventListener("stop", () => {
            release();
            resolve(new Blob(chunks, { type: recorder.mimeType }));
          });
          recorder.stop();
        }),
      cancel: () => {
        keep = false;
        recorder.stop();
        release();
      },
    };
  }

  /** 入力欄の中身の選んだ範囲を文字で置き換え、置き換えた後の中身と、挿入した文字の後ろの位置を返す */
  export function insertAtCursor(value: string, start: number, end: number, text: string): { value: string; caret: number } {
    // 範囲を超える位置は末尾にそろえる
    const from = Math.min(start, value.length);
    const to = Math.min(Math.max(end, from), value.length);
    return { value: `${value.slice(0, from)}${text}${value.slice(to)}`, caret: from + text.length };
  }

  /** 録音を始めてからの秒数を `m:ss` にする */
  export function formatElapsed(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const rest = Math.floor(seconds % 60);
    return `${minutes}:${String(rest).padStart(2, "0")}`;
  }

  /** ✓ を押したときの入力 */
  export type VoiceFinishInput = {
    /** 入力欄の中身 */
    body: string;
    /** `selectionStart` */
    start: number;
    /** `selectionEnd` */
    end: number;
    /** 設定の文字起こし後の挙動 */
    action: "send" | "insert";
    /** 向けた先（項目と箇所か、返信先のスレッド） */
    destination: { target: string | null; loc: Location | null } | { thread: string };
  };

  /** 録音を止めて文字起こしし、結果を入力欄の中身のカーソルの位置へ挿入して、挙動が send なら全文をすぐ送る */
  export async function finishVoice(
    recording: Recording,
    input: VoiceFinishInput,
    api: ReturnType<typeof voiceApi> = voiceApi(),
  ): Promise<VoiceOutcome> {
    const kept = { body: input.body, caret: null, entered: false, reason: null };
    const audio = await recording.stop();
    const result = await api.transcribe(audio);
    if (!result.ok) {
      // サービスが使えない: マイクのボタンを押せなくする
      if (result.status === 503) {
        return { ...kept, kind: "unavailable", detail: result.detail, reason: result.reason ?? "stopped" };
      }
      // 断られた・届かない: 入力欄の中身を残す
      return { ...kept, kind: "failed", detail: result.status === null ? VOICE_TEXT.failed : (result.detail ?? VOICE_TEXT.failed) };
    }
    const text = result.data?.text ?? "";
    // 話し声が無かった: 送信も挿入もしない
    if (text.trim() === "") return { ...kept, kind: "failed", detail: VOICE_TEXT.failed };
    const inserted = insertAtCursor(input.body, input.start, input.end, text);
    if (input.action === "insert") {
      return { kind: "inserted", body: inserted.value, caret: inserted.caret, entered: false, detail: null, reason: null };
    }
    const sent = await api.sendNow({ ...input.destination, body: inserted.value });
    if (!sent.ok) {
      return { kind: "failed", body: inserted.value, caret: inserted.caret, entered: false, detail: VOICE_TEXT.sendFailed, reason: null };
    }
    return { kind: "sent", body: "", caret: null, entered: sent.data?.entered ?? false, detail: null, reason: null };
  }
}
