// コメントの入力。詳細パネル・詳細の全画面の下端と、コメントの一覧の新しいスレッドの入力に置く、コメントをレビュー中に溜める入力欄と「レビューに追加」のボタン
import { useEffect, useId, useRef, useState, type CSSProperties, type FocusEvent, type ReactNode, type RefObject, type SyntheticEvent, type KeyboardEvent } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { locationLabel, type Location } from "@/shared/core/records";
import { formatElapsed } from "@/shared/core/voice";
import { cn } from "@/shared/lib/cn";

/** 溜める状態。idle は結果を出さない */
export type SendStatus = "idle" | "saving" | "saved" | "empty" | "failed" | "sent" | "inserted" | "reviewed" | "voice-failed";

/** 音声入力の状態（部品設計の `voice`） */
export type VoicePhase = "idle" | "disabled" | "recording" | "transcribing";

/** 音声入力の props（コメントの入力と返信の入力で共通） */
export type VoiceProps = {
  voice?: VoicePhase;
  /** マイクのボタンを押せない理由（`voice` が `disabled` のとき） */
  voiceReason?: string | null;
  /** 録音を始めてからの秒数（`voice` が `recording` のとき） */
  elapsed?: number;
  /** 録音中の音量の並び（古い順。0〜1。`voice` が `recording` のとき） */
  levels?: readonly number[];
  /** `status` が `sent` のとき、Claude Code へ入力したか */
  entered?: boolean;
  onVoiceStart?: () => void;
  onVoiceCancel?: () => void;
  onVoiceBlocked?: () => void;
};

export type SendFormProps = VoiceProps & {
  /** コメントを向ける項目の ID。null は項目を指さないコメント */
  target: string | null;
  /** 添えた箇所 */
  loc: Location | null;
  /** 入力欄の中身 */
  body: string;
  status: SendStatus;
  /** 溜めた後のレビュー中のコメントの件数 */
  count?: number | null;
  /** サーバーが返した溜められなかった理由。`failed` で null なら届かなかった */
  detail?: string | null;
  /** 畳んだ形（`target` が null のときだけ使う） */
  collapsed?: boolean;
  /** `target` が null のときの入力欄の読み上げの名前 */
  label?: string;
  /** 開いているか（`target` があるときだけ使う）。偽なら見出しの行だけを出す */
  open?: boolean;
  onSubmit: (target: string | null, loc: Location | null, body: string) => void;
  onInput: (body: string) => void;
  onClearLoc?: () => void;
  onCopyBody?: (body: string) => void;
  onFocus?: () => void;
  onBlur?: (body: string) => void;
  /** 開閉のボタンを押したとき（押した後の開閉） */
  onToggleOpen?: (open: boolean) => void;
  /** 録音中の ✓（入力欄の中身そのまま） */
  onVoiceDone?: (target: string | null, loc: Location | null, body: string) => void;
};

/** 溜めている印と文言を出すまでの待ち（ミリ秒）。すぐ終わる処理では点滅させない */
const SENDING_NOTICE_DELAY_MS = 1000;

/** 結果の行の文字の色（空・失敗は文言を本文の色で読ませる。印の色は `ResultMessage` が付ける） */
const RESULT_TONE = { idle: "", saving: "", saved: "", empty: "text-foreground", failed: "text-foreground", sent: "", inserted: "", reviewed: "", "voice-failed": "text-foreground" } as const satisfies Record<SendStatus, string>;

/** 項目を指さないコメントの入力欄の読み上げの名前 */
const NO_TARGET_LABEL = "項目を指さないコメント";

/** 音声入力の結果（送信した・挿入した・レビュー中に追加した・失敗した）。音声入力の結果でなければ null */
export const VoiceResult = ({ status, detail, entered }: { status: string; detail: string | null; entered: boolean }) => {
  if (status === "sent") {
    return (
      <>
        <Icon name="check" className="text-mark" />
        <span>{entered ? "送信し、Claude Code へ入力しました。" : "送信しました。Claude Code へは入力していません。"}</span>
      </>
    );
  }
  if (status === "inserted") {
    return (
      <>
        <Icon name="check" className="text-mark" />
        <span>文字起こしの結果を挿入しました。</span>
      </>
    );
  }
  if (status === "reviewed") {
    return (
      <>
        <Icon name="check" className="text-mark" />
        <span>文字起こしの結果をレビュー中に追加しました。</span>
      </>
    );
  }
  if (status === "voice-failed") {
    return (
      <>
        <Icon name="alert" className="text-st-review" />
        <span>{detail ?? "文字起こしできませんでした。もう一度お試しください。"}</span>
      </>
    );
  }
  return null;
};

/** 録音中・文字起こし中の結果の行。どちらでもなければ null */
export const VoiceProgress = ({ voice, elapsed }: { voice: VoicePhase; elapsed: number }) => {
  if (voice === "recording") {
    // 丸と経過の時間は見た目だけにし、読み上げは「録音中」だけにする
    return (
      <>
        <span aria-hidden="true" className="mt-1 size-2.5 shrink-0 rounded-full bg-st-review" />
        <span className="sr-only">録音中</span>
        <span aria-hidden="true" className="font-mono text-foreground tabular-nums">
          {formatElapsed(elapsed)}
        </span>
      </>
    );
  }
  if (voice === "transcribing") {
    return (
      <>
        <Icon name="spin" className="animate-spin" />
        <span className="sr-only">文字起こししています。</span>
      </>
    );
  }
  return null;
};

/** 録音中に入力欄の場所へ出す波形。音量 1 つが縦の棒 1 本で、読み上げない。録音中でなければ何も出さない */
export const VoiceWave = ({ voice, levels }: { voice: VoicePhase; levels: readonly number[] }) =>
  voice === "recording" ? (
    <div data-part="voice-wave" className="wave-send text-small" aria-hidden="true">
      {levels.map((level, index) => (
        // 棒は音量の並びの位置で見分ける（古い棒が左で捨てられ、並びが詰まる）
        <i key={index} className="wave-bar" style={{ "--lv": level } as CSSProperties} />
      ))}
    </div>
  ) : null;

/** 入力欄を書き換えられないか（溜めている間・録音中・文字起こし中） */
export const fieldLocked = (saving: boolean, voice: VoicePhase): boolean => saving || voice === "recording" || voice === "transcribing";

/** 録音を始めたとき・録音中の入力欄が付いたときは ✓ へ、終えたら入力欄の録音前の範囲へフォーカスを移す（入力欄は隠すだけで外さないため、選んだ範囲が残る） */
export const useVoiceFocus = (voice: VoicePhase, field: RefObject<HTMLTextAreaElement | null>, done: RefObject<HTMLButtonElement | null>): void => {
  const previous = useRef<VoicePhase>("idle");
  useEffect(() => {
    const before = previous.current;
    previous.current = voice;
    if (voice === "recording" && before !== "recording") done.current?.focus();
    if (voice === "idle" && (before === "recording" || before === "transcribing")) field.current?.focus();
  }, [voice, field, done]);
};

/** 入力欄の右に並べる音声入力のボタン（idle・disabled はマイクと submit、recording・transcribing は × と ✓） */
export const VoiceButtons = ({ voice, voiceReason, submit, doneRef, onStart, onCancel, onDone, onBlocked }: { voice: VoicePhase; voiceReason: string | null; submit: ReactNode; doneRef?: RefObject<HTMLButtonElement | null>; onStart?: () => void; onCancel?: () => void; onDone: () => void; onBlocked?: () => void }) => {
  const tipId = useId();
  if (voice === "recording" || voice === "transcribing") {
    const busy = voice === "transcribing";
    return (
      <div className="flex shrink-0 items-end gap-2">
        <Button type="button" variant="outline" size="icon" className="size-send disabled:bg-muted disabled:text-muted-foreground disabled:opacity-100 pointer-coarse:size-11" aria-label="キャンセル" title="キャンセル（録音を破棄）" disabled={busy} onClick={onCancel}>
          <Icon name="x" />
        </Button>
        <Button type="button" size="icon" className="size-send disabled:bg-muted disabled:text-muted-foreground disabled:opacity-100 aria-busy:disabled:cursor-progress pointer-coarse:size-11" ref={doneRef} aria-label={busy ? "文字起こし中" : "文字起こし"} title={busy ? "文字起こし中" : "文字起こし"} aria-busy={busy} disabled={busy} onClick={onDone}>
          <Icon name={busy ? "spin" : "check"} className={busy ? "animate-spin" : undefined} />
        </Button>
      </div>
    );
  }
  const blocked = voice === "disabled";
  return (
    <>
      <Button type="button" variant="outline" size="icon" className={cn("shrink-0 size-send pointer-coarse:size-11", blocked && "cursor-not-allowed bg-muted text-muted-foreground")} aria-label="音声で入力" title={blocked ? (voiceReason ?? undefined) : "音声で入力"} aria-disabled={blocked ? true : undefined} aria-describedby={blocked ? tipId : undefined} onClick={blocked ? onBlocked : onStart}>
        <Icon name="mic" />
      </Button>
      {blocked ? (
        <span id={tipId} className="sr-only">
          {voiceReason}
        </span>
      ) : null}
      {submit}
    </>
  );
};

/** 結果の印と文言 */
const ResultMessage = ({ status, count, detail, showSpinner, onCopy }: { status: SendStatus; count: number | null; detail: string | null; showSpinner: boolean; onCopy: () => void }) => {
  if (status === "saving") {
    return showSpinner ? (
      <>
        <Icon name="spin" className="animate-spin" />
        <span>レビューに追加しています</span>
      </>
    ) : null;
  }
  if (status === "saved") {
    return (
      <>
        <Icon name="check" className="text-mark" />
        <span>{`レビューに追加しました（レビュー中 ${String(count ?? 0)} 件）。`}</span>
      </>
    );
  }
  if (status === "empty") {
    return (
      <>
        <Icon name="alert" className="text-st-review" />
        <span>コメントを入れてから追加してください。</span>
      </>
    );
  }
  if (status === "failed") {
    if (detail !== null) {
      return (
        <>
          <Icon name="alert" className="text-st-review" />
          <span>{`レビューに追加できませんでした。${detail}`}</span>
        </>
      );
    }
    return (
      <>
        <Icon name="alert" className="text-st-review" />
        <span className="grid gap-1">
          <span>レビューに追加できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから追加してください。</span>
          <Button variant="ghost" size="icon" className="-ml-1 size-6 justify-self-start" aria-label="本文をコピー" title="本文をコピー" onClick={onCopy}>
            <Icon name="copy" />
          </Button>
        </span>
      </>
    );
  }
  return null;
};

/** 結果の行の中身（録音中・文字起こし中、音声入力の結果、溜めた結果の順に選ぶ） */
const FormMessage = ({ voice, elapsed, status, count, detail, entered, showSpinner, onCopy }: { voice: VoicePhase; elapsed: number; status: SendStatus; count: number | null; detail: string | null; entered: boolean; showSpinner: boolean; onCopy: () => void }) => {
  if (voice === "recording" || voice === "transcribing") return <VoiceProgress voice={voice} elapsed={elapsed} />;
  if (status === "sent" || status === "inserted" || status === "reviewed" || status === "voice-failed") return <VoiceResult status={status} detail={detail} entered={entered} />;
  return <ResultMessage status={status} count={count} detail={detail} showSpinner={showSpinner} onCopy={onCopy} />;
};

/** 入力欄の形ごとのクラス（畳んだ形は 1 行のまま伸ばさない） */
const FIELD_CLASS = {
  folded: "field-sizing-fixed h-8 resize-none overflow-hidden py-1",
  open: "field-sizing-content min-w-0 flex-1 resize-y field-send pointer-coarse:min-h-11",
} as const;

/** 入力欄の `aria-describedby`（畳んだ形は結果を出さないので指さない。添えた箇所があれば箇所も指す） */
const describedByOf = (folded: boolean, locId: string | null, messageId: string): string | undefined => {
  if (folded) return undefined;
  return locId === null ? messageId : `${locId} ${messageId}`;
};

/** 見出しの行（「{ID} へのコメント」・書きかけの印・開閉のボタン） */
const FormHead = ({ target, fieldId, bodyId, open, hasDraft, onToggleOpen }: { target: string; fieldId: string; bodyId: string; open: boolean; hasDraft: boolean; onToggleOpen?: (open: boolean) => void }) => {
  const toggleLabel = open ? "コメントの入力を閉じる" : "コメントの入力を開く";
  const name = (
    <>
      <span className="font-mono">{target}</span> へのコメント
    </>
  );
  return (
    <div className="flex min-w-0 items-center gap-2">
      {open ? (
        <label htmlFor={fieldId} className="min-w-0 truncate text-small text-muted-foreground">
          {name}
        </label>
      ) : (
        <span className="min-w-0 truncate text-small text-muted-foreground">{name}</span>
      )}
      {!open && hasDraft ? (
        <span className="flex shrink-0 items-center gap-1 text-small text-muted-foreground">
          <Icon name="edit" />
          書きかけ
        </span>
      ) : null}
      <Button variant="ghost" size="icon" className="ml-auto size-6 shrink-0" aria-expanded={open} aria-controls={bodyId} aria-label={toggleLabel} title={toggleLabel} onClick={() => onToggleOpen?.(!open)}>
        <Icon name="chev" className={open ? "rotate-90" : "-rotate-90"} />
      </Button>
    </div>
  );
};

/** 添えた箇所（名前・選んだ文・外す ×） */
const LocationChip = ({ loc, id, onClearLoc }: { loc: Location; id: string; onClearLoc?: () => void }) => (
  <div id={id} className="grid gap-1 rounded-control bg-muted p-2">
    <div className="flex items-center gap-1">
      <span className="flex-1 text-small font-medium">{locationLabel(loc)}</span>
      <Button variant="ghost" size="icon" aria-label="箇所を外す" title="箇所を外す" onClick={onClearLoc}>
        <Icon name="x" />
      </Button>
    </div>
    <blockquote className="m-0 line-clamp-3 text-small text-muted-foreground">{loc.text}</blockquote>
  </div>
);

export const SendForm = ({ target, loc, body, status, count = null, detail = null, collapsed = false, label = NO_TARGET_LABEL, open = true, voice = "idle", voiceReason = null, elapsed = 0, levels = [], entered = false, onSubmit, onInput, onClearLoc, onCopyBody, onFocus, onBlur, onToggleOpen, onVoiceStart, onVoiceCancel, onVoiceDone, onVoiceBlocked }: SendFormProps) => {
  const fieldId = useId();
  const messageId = `${fieldId}-msg`;
  const locId = `${fieldId}-loc`;
  const bodyId = `${fieldId}-body`;
  const folded = collapsed && target === null;
  const fieldRef = useRef<HTMLTextAreaElement>(null);
  const doneRef = useRef<HTMLButtonElement>(null);
  useVoiceFocus(voice, fieldRef, doneRef);
  // 空白だけで溜めようとしたか（次に書き換えるまで出す）
  const [empty, setEmpty] = useState(false);
  // 溜めている印は待ちの後に出す
  const [showSpinner, setShowSpinner] = useState(false);
  useEffect(() => {
    if (status !== "saving") return undefined;
    const timer = window.setTimeout(() => {
      setShowSpinner(true);
    }, SENDING_NOTICE_DELAY_MS);
    return () => {
      window.clearTimeout(timer);
      setShowSpinner(false);
    };
  }, [status]);
  const shown: SendStatus = empty ? "empty" : status;

  const trySave = (): void => {
    if (status === "saving") return;
    if (body.trim() === "") {
      setEmpty(true);
      return;
    }
    onSubmit(target, loc, body);
  };
  const handleSubmit = (event: SyntheticEvent<HTMLFormElement>): void => {
    event.preventDefault();
    trySave();
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    // 変換の確定の Enter では溜めない
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) {
      event.preventDefault();
      trySave();
    }
  };
  const handleBlur = (event: FocusEvent<HTMLFormElement>): void => {
    // フォーカスが部品の外へ出たときだけ知らせる
    const next = event.relatedTarget as Node | null;
    if (next === null || !event.currentTarget.contains(next)) onBlur?.(body);
  };

  const fieldClass = folded ? FIELD_CLASS.folded : FIELD_CLASS.open;
  // 入力欄と、その右の「レビューに追加」（アイコンだけのボタン）の行。結果は行の下に幅いっぱいで出す
  const field = (
    <Textarea
      ref={fieldRef}
      id={fieldId}
      name="body"
      rows={1}
      value={body}
      className={cn("aria-invalid:border-st-review", fieldClass)}
      aria-label={target === null ? label : undefined}
      aria-describedby={describedByOf(folded, target !== null && loc !== null ? locId : null, messageId)}
      aria-keyshortcuts="Control+Enter"
      aria-invalid={shown === "empty" ? true : undefined}
      readOnly={fieldLocked(status === "saving", voice)}
      // 録音中は波形と入れ替えて隠す（外さないので中身と選んだ範囲が残る）
      hidden={voice === "recording"}
      onChange={(event) => {
        setEmpty(false);
        onInput(event.target.value);
      }}
      onFocus={onFocus}
      onKeyDown={handleKeyDown}
    />
  );
  const line = folded ? (
    field
  ) : (
    <div className="flex items-end gap-2">
      {field}
      <VoiceWave voice={voice} levels={levels} />
      <VoiceButtons
        doneRef={doneRef}
        voice={voice}
        voiceReason={voiceReason}
        onStart={onVoiceStart}
        onCancel={onVoiceCancel}
        onBlocked={onVoiceBlocked}
        onDone={() => onVoiceDone?.(target, loc, body)}
        submit={
          <Button type="submit" size="icon" className="size-send disabled:bg-muted disabled:text-muted-foreground disabled:opacity-100 aria-busy:disabled:cursor-progress pointer-coarse:size-11" aria-label="レビューに追加" title="レビューに追加（Ctrl+Enter）" aria-busy={status === "saving"} disabled={status === "saving"}>
            <Icon name="comment" />
          </Button>
        }
      />
    </div>
  );
  const message = folded ? null : (
    <p id={messageId} role="status" className={cn("m-0 flex items-start gap-1 text-small text-muted-foreground empty:hidden", RESULT_TONE[shown])}>
      <FormMessage voice={voice} elapsed={elapsed} status={shown} count={count} detail={detail} entered={entered} showSpinner={showSpinner} onCopy={() => onCopyBody?.(body)} />
    </p>
  );

  return (
    <form noValidate data-id={target ?? undefined} data-collapsed={folded ? "" : undefined} className={cn("grid gap-1.5 border-t border-border p-3", folded && "gap-0 p-2", !open && target !== null && "py-2")} onSubmit={handleSubmit} onBlur={handleBlur}>
      {target === null ? (
        <>
          {line}
          {message}
        </>
      ) : (
        <>
          <FormHead target={target} fieldId={fieldId} bodyId={bodyId} open={open} hasDraft={body.trim() !== ""} onToggleOpen={onToggleOpen} />
          <div id={bodyId} hidden={!open} className="contents">
            {loc !== null ? <LocationChip loc={loc} id={locId} onClearLoc={onClearLoc} /> : null}
            {line}
            {message}
          </div>
        </>
      )}
    </form>
  );
};
