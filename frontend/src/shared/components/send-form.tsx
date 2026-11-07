// コメントの入力。詳細パネル・詳細の全画面の下端と、コメントの一覧の新しいスレッドの入力に置く、コメントをレビュー中に溜める入力欄と「レビューに追加」のボタン
import { useEffect, useId, useState, type FocusEvent, type SyntheticEvent, type KeyboardEvent } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { locationLabel, type Location } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

/** 溜める状態。idle は結果を出さない */
export type SendStatus = "idle" | "saving" | "saved" | "empty" | "failed";

export type SendFormProps = {
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
  onSubmit: (target: string | null, loc: Location | null, body: string) => void;
  onInput: (body: string) => void;
  onClearLoc?: () => void;
  onCopyBody?: (body: string) => void;
  onFocus?: () => void;
  onBlur?: (body: string) => void;
};

/** 溜めている印と文言を出すまでの待ち（ミリ秒）。すぐ終わる処理では点滅させない */
const SENDING_NOTICE_DELAY_MS = 1000;

/** 項目を指さないコメントの入力欄の読み上げの名前 */
const NO_TARGET_LABEL = "項目を指さないコメント";

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
        <Icon name="check" />
        <span>{`レビューに追加しました（レビュー中 ${String(count ?? 0)} 件）。`}</span>
      </>
    );
  }
  if (status === "empty") {
    return (
      <>
        <Icon name="alert" />
        <span>コメントを入れてから追加してください。</span>
      </>
    );
  }
  if (status === "failed") {
    if (detail !== null) {
      return (
        <>
          <Icon name="alert" />
          <span>{`レビューに追加できませんでした。${detail}`}</span>
        </>
      );
    }
    return (
      <>
        <Icon name="alert" />
        <span className="grid gap-1">
          <span>レビューに追加できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから追加してください。</span>
          <Button variant="ghost" className="justify-self-start" onClick={onCopy}>
            <Icon name="copy" />
            本文を写す
          </Button>
        </span>
      </>
    );
  }
  return null;
};

export const SendForm = ({ target, loc, body, status, count = null, detail = null, collapsed = false, label = NO_TARGET_LABEL, onSubmit, onInput, onClearLoc, onCopyBody, onFocus, onBlur }: SendFormProps) => {
  const fieldId = useId();
  const messageId = `${fieldId}-msg`;
  const locId = `${fieldId}-loc`;
  const folded = collapsed && target === null;
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

  return (
    <form noValidate data-id={target ?? undefined} className={cn("grid gap-1.5 border-t border-border p-3", folded && "gap-0 p-2")} onSubmit={handleSubmit} onBlur={handleBlur}>
      {target === null ? null : (
        <label htmlFor={fieldId} className="text-small text-muted-foreground">
          <span className="font-mono">{target}</span> へのコメント
        </label>
      )}
      {target !== null && loc !== null ? (
        <div id={locId} className="grid gap-1 rounded-control bg-muted p-2">
          <div className="flex items-center gap-1">
            <span className="flex-1 text-small font-medium">{locationLabel(loc)}</span>
            <Button variant="ghost" size="icon" aria-label="箇所を外す" title="箇所を外す" onClick={onClearLoc}>
              <Icon name="x" />
            </Button>
          </div>
          <blockquote className="m-0 line-clamp-3 text-small text-muted-foreground">{loc.text}</blockquote>
        </div>
      ) : null}
      <Textarea
        id={fieldId}
        name="body"
        rows={1}
        value={body}
        className={cn("field-sizing-content max-h-48 resize-none", folded && "max-h-9")}
        aria-label={target === null ? label : undefined}
        aria-describedby={folded ? undefined : target !== null && loc !== null ? `${locId} ${messageId}` : messageId}
        aria-keyshortcuts="Control+Enter"
        aria-invalid={shown === "empty" ? true : undefined}
        readOnly={status === "saving"}
        onChange={(event) => {
          setEmpty(false);
          onInput(event.target.value);
        }}
        onFocus={onFocus}
        onKeyDown={handleKeyDown}
      />
      {folded ? null : (
        <div className="flex items-start gap-2">
          <p id={messageId} role="status" className="m-0 flex flex-1 items-start gap-1 text-small text-muted-foreground">
            <ResultMessage status={shown} count={count} detail={detail} showSpinner={showSpinner} onCopy={() => onCopyBody?.(body)} />
          </p>
          <Button type="submit" title="レビューに追加（Ctrl+Enter）" disabled={status === "saving"}>
            <Icon name="comment" />
            レビューに追加
          </Button>
        </div>
      )}
    </form>
  );
};
