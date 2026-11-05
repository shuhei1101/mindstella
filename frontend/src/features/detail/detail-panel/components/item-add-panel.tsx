// 項目の追加の入力（画面設計『検討事項.tsx』の「項目を追加」）。タイトルを離れたときに `item-add` を 1 件溜め、残りのキーと案は返った仮の ID で同じ編集の `value` を書き換える
import { useRef, useState } from "react";

import { DetailEditor, type EditChange } from "@/features/detail/detail-panel/components/detail-editor";
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { NEW_ID_PREFIX, type PendingEdit } from "@/shared/core/edits";
import { KIND_LABEL, tagNames, type Item, type Kind, type Option, type RecordIndex } from "@/shared/core/records";
import { useAddEdit } from "@/shared/hooks/use-edits";
import { useEditSessionStore } from "@/shared/stores/edit-session-store";

/** 案を採用したときの検討事項の状態 */
const ADOPTED_DECISION_STATUS = "決定済み";

/** 今日の日付（JST の YYYY-MM-DD） */
const todayJst = (): string => new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" }).format(new Date());

/** 追加する項目の最初の値（スキーマで必須のキーを、保存で弾かれない値で埋める） */
export const addDefaults = (kind: Kind, today: string): Record<string, unknown> => {
  const defaults: Record<Kind, Record<string, unknown>> = {
    decisions: { status: "未整理" },
    tasks: { status: "未着手", kind: "作業" },
    research: { question: "" },
    docs: { status: "下書き", kind: "文書", deliverable: false, body: "" },
    terms: { meaning: "" },
    notes: { content: "" },
    logs: { date: today },
  };
  return defaults[kind];
};

/** 案の操作を `value` の `options` に当てる（`adopt` では選んだ案だけを採用にし、状態を決定済みにする） */
const applyOption = (value: Record<string, unknown>, { op, key, value: input }: EditChange): void => {
  let options = ((value["options"] as Option[] | undefined) ?? []).map((option) => ({ ...option }));
  const content = (input as { content?: string } | null)?.content ?? "";
  if (op === "option-add") options.push({ key, content });
  else if (op === "option-edit") options = options.map((option) => (option.key === key ? { ...option, content } : option));
  else if (op === "option-remove") options = options.filter((option) => option.key !== key);
  else if (op === "adopt") {
    for (const option of options) {
      if (option.key === input) option.adopted = true;
      else delete option.adopted;
    }
    if (input !== null) value["status"] = ADOPTED_DECISION_STATUS;
  }
  if (options.length === 0) delete value["options"];
  else value["options"] = options;
};

/** 送信の並び。前の送信が終わってから次を送る */
type AddSend = { target: string | null; value: Record<string, unknown>; tail: Promise<void> };

export type ItemAddPanelProps = { kind: Kind; target: string | null; index: RecordIndex; edits: readonly PendingEdit[] };

export const ItemAddPanel = ({ kind, target, index, edits }: ItemAddPanelProps) => {
  const add = useAddEdit();
  const openAdded = useEditSessionStore((state) => state.openAdded);
  const closeAdd = useEditSessionStore((state) => state.closeAdd);
  const [failure, setFailure] = useState<string | null>(null);
  const initial = (): Record<string, unknown> => {
    const entry = edits.find((edit) => edit.op === "item-add" && edit.target === target);
    return entry === undefined ? addDefaults(kind, todayJst()) : { ...(entry.value as Record<string, unknown>) };
  };
  const [value, setValue] = useState(initial);
  const send = useRef<AddSend>({ target, value, tail: Promise.resolve() });
  const onChange = (change: EditChange): void => {
    const current = send.current;
    current.tail = current.tail.then(async () => {
      const next = { ...current.value };
      if (change.op !== "set") applyOption(next, change);
      else if (change.value === null) delete next[change.key];
      else next[change.key] = change.value;
      current.value = next;
      setValue(next);
      // タイトルを書くまでは溜めない
      if (current.target === null && (typeof next["title"] !== "string" || next["title"].trim() === "")) return;
      try {
        setFailure(null);
        const reply = await add.mutateAsync({ ...(current.target === null ? {} : { target: current.target }), op: "item-add", key: kind, value: next });
        if (current.target === null) {
          current.target = (reply.data as { target: string }).target;
          openAdded(kind, current.target);
        }
      } catch (error) {
        setFailure((error as Error).message);
      }
    });
  };
  const item = { id: target ?? NEW_ID_PREFIX, title: "", ...value } as Item;
  return (
    <aside aria-label={`${KIND_LABEL[kind]}を追加`} className="relative flex min-h-0 w-160 flex-none flex-col border-l border-border bg-card max-lg:fixed max-lg:inset-0 max-lg:z-30 max-lg:w-full">
      <div className="flex items-center gap-1 border-b border-border-soft p-2">
        <h2 className="m-0 flex-1 text-small font-semibold">{`${KIND_LABEL[kind]}を追加`}</h2>
        <Button variant="ghost" size="icon" aria-label="追加の入力を閉じる" onClick={closeAdd}>
          <Icon name="x" />
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <DetailEditor kind={kind} item={item} settings={index.data.settings} marks={{}} blocked={{}} removing={false} removedOptions={[]} referrers={[]} usedTags={[...new Set([...index.byId.values()].flatMap(({ item: other }) => tagNames(other.tags)))]} body={typeof value["body"] === "string" ? value["body"] : ""} onChange={onChange} onRemove={closeAdd} onCancelRemove={closeAdd} />
        {failure === null ? null : (
          <p role="alert" className="mx-3 flex items-center gap-1 text-small text-destructive">
            <Icon name="alert" className="size-4" />
            {failure}
          </p>
        )}
      </div>
    </aside>
  );
};
