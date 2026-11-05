// 保存待ちのパネル（画面設計『保存待ちのパネル.tsx』）。保存待ちの編集を項目ごとに並べ、1 件ずつ取り消し、まとめて保存する
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Icon } from "@/shared/components/icon";
import { BlockedNote } from "@/shared/components/blocked-note";
import { TagList } from "@/shared/components/tag-list";
import { Button } from "@/shared/components/ui/button";
import { SETTINGS_TARGET, type PendingEdit } from "@/shared/core/edits";
import { toText } from "@/shared/core/format";
import { KIND_LABEL, type Kind, type RecordIndex, type Tag } from "@/shared/core/records";
import { useCancelEdit, useSaveEdits } from "@/shared/hooks/use-edits";
import { useEditSessionStore } from "@/shared/stores/edit-session-store";

const SETTING_LABELS: Record<string, string> = { summary: "題名", description: "説明", playbooks: "プレイブック", phases: "フェーズ", target_label: "最上位の軸の呼び名", goal: "ゴール", targets: "対象", categories: "カテゴリー", links: "関連する場所", history_limit: "保持する回数" };

const KEY_LABELS: Record<string, string> = { status: "状態", title: "タイトル", target: "機能", category: "カテゴリー", phase: "フェーズ", tags: "タグ", depends_on: "依存先", answer: "決定内容", reason: "理由", body: "本文", result: "結果", kind: "種類", question: "問い", conclusion: "結論", confidence: "確からしさ", related: "関連", withdrawn: "取り下げ", meaning: "意味", aliases: "別名", content: "内容", date: "日付", deliverable: "納品物", description: "説明" };

/** 値を 1 行の文字にする（空は「（空）」、配列は「、」でつなぐ） */
const flat = (value: unknown): string => {
  if (value === undefined || value === null || value === "") return "（空）";
  if (Array.isArray(value)) return value.length === 0 ? "（空）" : value.map(flat).join("、");
  if (value === true) return "はい";
  if (value === false) return "いいえ";
  if (typeof value === "object") return JSON.stringify(value);
  return toText(value).replace(/\s+/g, " ");
};

type RowText = { what: string; before: string | Tag[] | null; after: string | Tag[] | null };

const contentOf = (value: unknown): unknown => (value as { content?: unknown } | null)?.content;

const rowText = (edit: PendingEdit): RowText => {
  const key = edit.key ?? "";
  switch (edit.op) {
    case "item-add":
      return { what: "項目を追加", before: null, after: flat((edit.value as { title?: string } | null)?.title) };
    case "item-remove":
      return { what: "項目を削除", before: null, after: null };
    case "setting":
      return { what: SETTING_LABELS[key] ?? key, before: flat(edit.before), after: flat(edit.value) };
    case "option-add":
      return { what: `案 ${key} を追加`, before: null, after: flat(contentOf(edit.value)) };
    case "option-remove":
      return { what: `案 ${key} を削除`, before: null, after: null };
    case "option-edit":
      return { what: `案 ${key}`, before: flat(contentOf(edit.before) ?? edit.before), after: flat(contentOf(edit.value)) };
    case "adopt":
      return { what: "採用する案", before: flat(edit.before ?? "なし"), after: flat(edit.value) };
    default:
      if (key === "body") return { what: "本文", before: null, after: null };
      if (key === "tags") return { what: "タグ", before: Array.isArray(edit.before) ? (edit.before as Tag[]) : flat(edit.before), after: Array.isArray(edit.value) ? (edit.value as Tag[]) : flat(edit.value) };
      return { what: KEY_LABELS[key] ?? key, before: flat(edit.before), after: flat(edit.value) };
  }
};

const groupEdits = (edits: readonly PendingEdit[]): { target: string; edits: PendingEdit[] }[] => {
  const groups: { target: string; edits: PendingEdit[] }[] = [];
  for (const edit of edits) {
    const found = groups.find((group) => group.target === edit.target);
    if (found === undefined) groups.push({ target: edit.target, edits: [edit] });
    else found.edits.push(edit);
  }
  return groups;
};

const describeTarget = (target: string, edits: readonly PendingEdit[], index: RecordIndex): { kind: string; id: string | null; title: string } => {
  if (target === SETTINGS_TARGET) return { kind: "設定", id: null, title: index.data.settings.summary };
  const added = edits.find((edit) => edit.op === "item-add");
  if (added !== undefined) return { kind: `${KIND_LABEL[(added.key ?? "") as Kind]}を追加`, id: null, title: (added.value as { title?: string }).title ?? "" };
  const entry = index.byId.get(target);
  return entry === undefined ? { kind: "項目", id: target, title: "" } : { kind: KIND_LABEL[entry.kind], id: target, title: entry.item.title };
};

const valueView = (value: string | Tag[]): ReactNode => {
  if (typeof value === "string") return value;
  return value.length === 0 ? flat(value) : <TagList values={value} />;
};

export type PendingEditsPanelProps = { edits: readonly PendingEdit[]; index: RecordIndex; onClose: () => void; onOpen: (target: string) => void };

export const PendingEditsPanel = ({ edits, index, onClose, onOpen }: PendingEditsPanelProps) => {
  const save = useSaveEdits();
  const cancel = useCancelEdit();
  const blocked = useEditSessionStore((state) => state.blocked);
  const setBlocked = useEditSessionStore((state) => state.setBlocked);
  const alert = useRef<HTMLDivElement>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [saved, setSaved] = useState<number | null>(null);
  const removals = edits.filter((edit) => edit.op === "item-remove").length;
  const blockedBy = new Map(blocked.map((entry) => [entry.id, entry]));
  const blockedEdits = edits.filter((edit) => blockedBy.has(edit.id));
  const nameOf = (edit: PendingEdit): string => {
    const who = describeTarget(edit.target, edits.filter((other) => other.target === edit.target), index);
    return `${who.id ?? who.kind} の${rowText(edit).what}`;
  };
  // 書き込めない編集の知らせを出したら、知らせへフォーカスを移す
  useEffect(() => {
    if (blocked.length > 0) alert.current?.focus();
  }, [blocked]);
  const label = save.isPending ? "保存しています…" : removals > 0 ? `まとめて保存する（${String(removals)} 件を削除）` : "まとめて保存する";
  return (
    <aside id="pending-panel" aria-label="保存待ちの編集" className="fixed inset-y-0 left-0 z-30 flex w-96 max-w-full flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border-soft p-2">
        <h2 className="m-0 text-small font-semibold">保存待ち</h2>
        <span className="text-xs text-muted-foreground">{edits.length} 件</span>
        <Button variant="ghost" size="icon" aria-label="保存待ちの編集を閉じる" className="ml-auto" onClick={onClose}>
          <Icon name="x" />
        </Button>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto p-2">
        {blockedEdits.length > 0 ? (
          <div ref={alert} role="alert" tabIndex={-1} className="rounded-control border border-destructive p-2 text-small">
            <p className="m-0 flex items-center gap-1 font-medium">
              <Icon name="alert" className="size-4" />
              {`${String(blockedEdits.length)} 件の編集を書き込めないため、何も保存していません。`}
            </p>
            <ul className="my-1">
              {blockedEdits.map((edit) => (
                <li key={edit.id}>
                  <button type="button" className="cursor-pointer text-left underline" onClick={() => { document.getElementById(`pe-row-${edit.id}`)?.querySelector("button")?.focus(); }}>
                    {nameOf(edit)}
                  </button>
                </li>
              ))}
            </ul>
            <p className="m-0">書き込めない編集を取り消してから、もう一度保存してください。</p>
          </div>
        ) : null}
        {failure === null ? null : (
          <p role="alert" className="flex items-center gap-1 text-small text-destructive">
            <Icon name="alert" className="size-4" />
            {`保存できませんでした。${failure}`}
          </p>
        )}
        {saved === null ? null : (
          <p role="status" className="flex items-center gap-1 text-small">
            <Icon name="check" className="size-4" />
            {`${String(saved)} 件を保存しました。`}
          </p>
        )}
        {edits.length === 0 ? <p className="text-small text-muted-foreground">保存待ちの編集はありません。</p> : null}
        {groupEdits(edits).map((group) => {
          const who = describeTarget(group.target, group.edits, index);
          return (
            <section key={group.target} className="flex flex-col gap-1">
              <h3 className="m-0">
                <button type="button" aria-label={`${who.id ?? who.kind}「${who.title}」を開く`} className="flex cursor-pointer items-center gap-1 text-left text-small font-medium" onClick={() => { onOpen(group.target); }}>
                  <span className="text-xs text-muted-foreground">{who.kind}</span>
                  {who.id === null ? null : <span className="font-mono text-xs">{who.id}</span>}
                  <span>{who.title}</span>
                </button>
              </h3>
              <ul className="flex flex-col gap-1">
                {group.edits.map((edit) => {
                  const text = rowText(edit);
                  const entry = blockedBy.get(edit.id);
                  return (
                    <li key={edit.id} id={`pe-row-${edit.id}`} className="flex items-start gap-2 rounded-control border border-border-soft p-1">
                      <div className="flex min-w-0 flex-1 flex-col text-small">
                        <span className="inline-flex items-center gap-1">
                          {edit.op === "item-remove" ? <Icon name="trash" className="size-3" /> : null}
                          {text.what}
                        </span>
                        {text.after === null ? null : (
                          <span className="flex flex-wrap items-center gap-1 text-xs">
                            {text.before === null ? null : (
                              <>
                                <del>
                                  <span className="sr-only">前: </span>
                                  {valueView(text.before)}
                                </del>
                                <span aria-hidden="true">→</span>
                              </>
                            )}
                            <ins>
                              <span className="sr-only">後: </span>
                              {valueView(text.after)}
                            </ins>
                          </span>
                        )}
                        {entry === undefined ? null : <BlockedNote blocked={entry} updated={index.byId.get(edit.target)?.item.updated ?? null} onOpen={onOpen} />}
                      </div>
                      <Button variant="ghost" aria-label={`${who.id ?? who.kind} の${text.what}の編集を取り消す`} onClick={() => { cancel.mutate(edit.id); }}>
                        <Icon name="undo" />
                        <span className="max-sm:sr-only">取り消す</span>
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
      </div>
      <div className="flex flex-col gap-1 border-t border-border-soft p-2">
        {edits.length === 0 ? null : <p className="m-0 text-xs text-muted-foreground">{`${String(edits.length)} 件${removals > 0 ? `（うち削除 ${String(removals)} 件）` : ""}をワークスペースへ書き込みます。`}</p>}
        <Button
          disabled={save.isPending || edits.length === 0}
          aria-busy={save.isPending || undefined}
          onClick={() => {
            const count = edits.length;
            setFailure(null);
            setSaved(null);
            save.mutate(undefined, {
              onSuccess: ({ blocked: next }) => {
                setBlocked(next);
                if (next.length === 0) setSaved(count);
              },
              onError: (error) => { setFailure(error.message); },
            });
          }}
        >
          <Icon name="save" />
          {label}
        </Button>
      </div>
    </aside>
  );
};
