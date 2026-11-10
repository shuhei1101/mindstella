// コメント・返信の入力の録音と、カーソルの位置への挿入（今の画面の `core/voice.ts` と同じ振る舞い）

/** `MediaRecorder.isTypeSupported` が真の最初の形で録る（今の画面と同じ並び） */
export const VOICE_MIME_TYPES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"] as const;

/** サーバーが返さない理由の文（今の画面の `VOICE_TEXT` と同じ文） */
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

/** 録音を始められなかったときに投げるエラー */
export class RecordingError extends Error {
  readonly reason: RecordingFailure;

  constructor(reason: RecordingFailure) {
    super(reason);
    this.name = "RecordingError";
    this.reason = reason;
  }
}

/** navigator.mediaDevices.getUserMedia と MediaRecorder を持つかを返す */
export const micSupported = (): boolean =>
  typeof (navigator.mediaDevices as MediaDevices | undefined)?.getUserMedia === "function" && typeof (globalThis as { MediaRecorder?: unknown }).MediaRecorder === "function";

/** マイクの許可を得て録音を始め、録音を返す。許可の拒否は `reason` が `denied`、それ以外は `no-microphone` の `RecordingError` で断る */
export const startRecording = async (): Promise<Recording> => {
  if (!micSupported()) throw new RecordingError("no-microphone");
  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error) {
    // 許可を拒否した: 許可が要る旨を出す。それ以外（マイクが無いなど）は使えない旨を出す
    const name = error instanceof DOMException ? error.name : "";
    throw new RecordingError(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "no-microphone");
  }
  const mimeType = VOICE_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
  const recorder = new MediaRecorder(stream, mimeType === undefined ? undefined : { mimeType });
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
};

/** 入力欄の中身の選んだ範囲を文字で置き換え、中身と挿入した文字の後ろの位置を返す（範囲を超える位置は末尾にそろえる） */
export const insertAtCursor = (value: string, start: number, end: number, text: string): { value: string; caret: number } => {
  const from = Math.min(start, value.length);
  const to = Math.min(Math.max(end, from), value.length);
  return { value: `${value.slice(0, from)}${text}${value.slice(to)}`, caret: from + text.length };
};

/** 秒数を `m:ss` にする */
export const formatElapsed = (seconds: number): string => `${String(Math.floor(seconds / 60))}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
