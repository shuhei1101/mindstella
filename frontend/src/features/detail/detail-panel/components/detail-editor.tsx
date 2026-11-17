// 詳細の編集の表示。キーごとの入力と、検討事項の案の入力、項目の削除
import { useState, type ReactNode } from "react";

import { BlockedNote } from "@/shared/components/blocked-note";
import { ChipsInput } from "@/shared/components/chips-input";
import { Icon } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Input } from "@/shared/components/ui/input";
import { Select } from "@/shared/components/ui/select";
import { Textarea } from "@/shared/components/ui/textarea";
import { NEW_ID_PREFIX, type BlockedEdit, type PendingEdit, type PendingMarkKind } from "@/shared/core/edits";
import { formatJst } from "@/shared/core/format";
import { DECISION_STATUSES, DOC_STATUSES, KIND_LABEL, refsOf, relationValidator, TASK_STATUSES, type Item, type Kind, type RecordIndex, type Relation, type RelationType, type Settings, type Tag } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

type Input = "text" | "textarea" | "select" | "tags" | "refs" | "relations" | "check" | "body" | "options";

const key = (name: string, input: Input) => ({ key: name, input });

const EDITABLE_KEYS: Record<Kind, { key: string; input: Input }[]> = {
  decisions: [key("status", "select"), key("title", "text"), key("target", "select"), key("category", "select"), key("phase", "select"), key("tags", "tags"), key("related", "relations"), key("options", "options"), key("answer", "textarea"), key("reason", "textarea"), key("body", "body")],
  tasks: [key("status", "select"), key("title", "text"), key("target", "select"), key("kind", "select"), key("tags", "tags"), key("related", "relations"), key("result", "textarea"), key("body", "body")],
  research: [key("title", "text"), key("question", "textarea"), key("conclusion", "textarea"), key("confidence", "select"), key("tags", "tags"), key("related", "relations"), key("withdrawn", "check"), key("reason", "textarea"), key("body", "body")],
  docs: [key("status", "select"), key("title", "text"), key("kind", "text"), key("deliverable", "check"), key("tags", "tags"), key("related", "relations"), key("withdrawn", "check"), key("reason", "textarea"), key("body", "body")],
  terms: [key("title", "text"), key("meaning", "textarea"), key("aliases", "refs"), key("tags", "tags"), key("withdrawn", "check"), key("reason", "textarea"), key("body", "body")],
  notes: [key("title", "text"), key("content", "textarea"), key("tags", "tags"), key("related", "relations"), key("withdrawn", "check"), key("reason", "textarea"), key("body", "body")],
  logs: [key("title", "text"), key("date", "text"), key("related", "relations"), key("withdrawn", "check"), key("reason", "textarea"), key("body", "body")],
};

const ADD_KEYS: Record<Kind, string[]> = {
  decisions: ["status", "title", "options", "tags", "body"],
  tasks: ["status", "title", "kind", "tags", "body"],
  research: ["title", "question", "tags", "body"],
  docs: ["status", "title", "kind", "deliverable", "tags", "body"],
  terms: ["title", "meaning", "tags", "body"],
  notes: ["title", "content", "tags", "body"],
  logs: ["title", "date", "body"],
};

/** キーの呼び名 */
export const KEY_LABELS: Record<string, string> = {
  status: "状態", title: "タイトル", target: "機能", category: "カテゴリー", phase: "フェーズ", tags: "タグ", answer: "決定内容", reason: "理由", body: "本文", result: "結果", kind: "種類", question: "問い", conclusion: "結論", confidence: "確からしさ", related: "関係", withdrawn: "取り下げ", meaning: "意味", aliases: "別名", content: "内容", date: "日付", deliverable: "納品物", description: "説明",
};

const TASK_KINDS = ["作業", "調査", "検証"];
const CONFIDENCES = ["高", "中", "低"];
const CHIP_HINTS: Record<string, string> = { tags: "タグを入れる", aliases: "別名を入れる" };

/** 種類ごとに関係の入力へ並べる関連の種類（表示の順） */
const RELATION_TYPES: Record<Kind, RelationType[]> = {
  decisions: ["depends_on", "parent", "see_also"],
  tasks: ["for", "depends_on", "see_also"],
  research: ["see_also"],
  docs: ["see_also"],
  terms: ["see_also"],
  notes: ["see_also"],
  logs: ["see_also"],
};

/** 関連の種類の表示名 */
const RELATION_LABELS: Record<RelationType, string> = { depends_on: "前提", parent: "親", for: "向けた検討事項", see_also: "関連" };

const labelOf = (kind: Kind, name: string): string => {
  if (name === "title" && kind === "terms") return "用語";
  if (name === "reason" && kind !== "decisions" && kind !== "tasks") return "取り下げた理由";
  return KEY_LABELS[name] ?? name;
};

const selectOptions = (kind: Kind, name: string, settings: Settings): readonly string[] => {
  if (name === "status") return kind === "decisions" ? DECISION_STATUSES : kind === "tasks" ? TASK_STATUSES : DOC_STATUSES;
  if (name === "kind") return TASK_KINDS;
  if (name === "confidence") return CONFIDENCES;
  if (name === "target") return settings.targets.map((target) => target.name);
  if (name === "category") return settings.categories.map((category) => category.name);
  return settings.phases;
};

/** 編集の表示から知らせる、溜める編集 1 件 */
export type EditChange = { op: PendingEdit["op"]; key: string; value: unknown };

export type DetailEditorProps = {
  kind: Kind;
  item: Item;
  settings: Settings;
  marks: Record<string, PendingMarkKind>;
  /** キーか案の記号 → 直前の保存で書き込めなかった編集 */
  blocked: Record<string, BlockedEdit>;
  removing: boolean;
  removedOptions: readonly string[];
  referrers: readonly string[];
  usedTags: readonly string[];
  body: string | undefined;
  /** 記録の索引（関係の入力で、入れた ID かタイトルを項目に当てる。渡さなければ入れた値をそのまま追加する） */
  index?: RecordIndex;
  onChange: (change: EditChange) => void;
  onRemove: () => void;
  onCancelRemove: () => void;
};

/** 関係の入力（種類ごとに見出しを置き、その下にチップの入力を 1 つずつ並べる）。どれかが変わったら全ての種類の並びを `related` にして溜める */
const RelationsField = ({ kind, item, mark, removing, index, onChange }: { kind: Kind; item: Item; mark: PendingMarkKind | undefined; removing: boolean; index: RecordIndex | undefined; onChange: (related: Relation[]) => void }) => {
  const types = RELATION_TYPES[kind];
  const current = new Map<RelationType, string[]>(types.map((type) => [type, refsOf(item, type)]));
  const empty = [...current.values()].every((ids) => ids.length === 0);
  return (
    <div data-key="related" className="flex flex-col gap-1">
      <div className="flex items-center gap-1 text-small font-medium">
        <span>関係</span>
        {mark === undefined ? null : <PendingMark kind={mark} compact />}
      </div>
      {empty ? <p className="m-0 text-small text-muted-foreground">なし</p> : null}
      {types.map((type) => {
        const controlId = `pe-${item.id.replace(/[^A-Za-z0-9]/g, "")}-related-${type}`;
        return (
          <div key={type} data-type={type} className="flex flex-col gap-1">
            <label htmlFor={controlId} className="text-xs text-muted-foreground">
              {RELATION_LABELS[type]}
            </label>
            <ChipsInput
              controlId={controlId}
              name={RELATION_LABELS[type]}
              hint="ID かタイトル"
              values={current.get(type) ?? []}
              monospace
              disabled={removing}
              validate={index === undefined ? undefined : relationValidator(type, kind, index)}
              onChange={(values) => {
                const next = new Map(current);
                next.set(type, values.map((value) => (typeof value === "string" ? value : value.name)));
                onChange(types.flatMap((each) => (next.get(each) ?? []).map((to) => ({ to, type: each }))));
              }}
            />
          </div>
        );
      })}
    </div>
  );
};

const Field = ({ label, controlId, required, mark, children }: { label: string; controlId: string; required?: boolean; mark: PendingMarkKind | undefined; children: ReactNode }) => (
  <div className="flex flex-col gap-1">
    <div className="flex items-center gap-1 text-small font-medium">
      <label htmlFor={controlId}>{label}</label>
      {required === true ? <span className="text-xs text-destructive">必須</span> : null}
      {mark === undefined ? null : <PendingMark kind={mark} compact />}
    </div>
    {children}
  </div>
);

// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
export const DetailEditor = ({ kind, item, settings, marks, blocked, removing, removedOptions, referrers, usedTags, body, index, onChange, onRemove, onCancelRemove }: DetailEditorProps) => {
  const adding = item.id.startsWith(NEW_ID_PREFIX);
  const [titleEmpty, setTitleEmpty] = useState(false);
  const [drafts, setDrafts] = useState<{ key: string; content: string }[]>([]);
  const keys = adding ? EDITABLE_KEYS[kind].filter((entry) => ADD_KEYS[kind].includes(entry.key)) : EDITABLE_KEYS[kind];
  const record = item as unknown as Record<string, unknown>;
  const set = (name: string, value: unknown): void => { onChange({ op: "set", key: name, value }); };
  // eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
  const field = (name: string, input: Input) => {
    const controlId = `pe-${item.id.replace(/[^A-Za-z0-9]/g, "")}-${name}`;
    const value = name === "body" ? (body ?? "") : record[name];
    const label = labelOf(kind, name);
    const text = typeof value === "string" ? value : "";
    if (input === "select") {
      return (
        <Select id={controlId} name={name} disabled={removing} value={text} onChange={(event) => { set(name, event.target.value === "" ? null : event.target.value); }}>
          {name === "status" || name === "kind" ? null : <option value="">（なし）</option>}
          {selectOptions(kind, name, settings).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </Select>
      );
    }
    if (input === "check") return <Checkbox id={controlId} name={name} checked={value === true} disabled={removing} onChange={(event) => { set(name, event.target.checked); }} />;
    if (input === "tags" || input === "refs") return <ChipsInput controlId={controlId} name={label} hint={CHIP_HINTS[name] ?? `${label}を入れる`} values={Array.isArray(value) ? (value as (Tag | string)[]) : []} suggestions={name === "tags" ? usedTags : null} monospace={name !== "tags"} mainToggle={name === "tags"} disabled={removing} onChange={(next) => { set(name, next); }} />;
    if (input === "textarea" || input === "body") return <Textarea key={text} id={controlId} name={name} rows={input === "body" ? 8 : 3} disabled={removing} defaultValue={text} onBlur={(event) => { if (event.target.value !== text) set(name, event.target.value === "" && input !== "body" ? null : event.target.value); }} />;
    return (
      <>
        <Input
          key={text}
          id={controlId}
          name={name}
          type={name === "date" ? "date" : "text"}
          defaultValue={text}
          autoComplete="off"
          disabled={removing}
          required={name === "title"}
          aria-invalid={name === "title" && titleEmpty}
          onBlur={(event) => {
            const next = event.target.value;
            if (name === "title") {
              setTitleEmpty(next.trim() === "");
              if (next.trim() === "") return;
            }
            if (next !== text) set(name, next === "" && name !== "title" ? null : next);
          }}
        />
        {name === "title" && titleEmpty ? (
          <p role="alert" className="flex items-center gap-1 text-small text-destructive">
            <Icon name="alert" className="size-3" />
            タイトルを書いてください。
          </p>
        ) : null}
      </>
    );
  };
  const options = item.options ?? [];
  const shownDrafts = drafts.filter((draft) => !options.some((option) => option.key === draft.key));
  return (
    <form noValidate aria-label={adding ? `${KIND_LABEL[kind]}を追加` : `${item.id} を編集`} data-id={item.id} className="flex flex-col gap-3 p-3" onSubmit={(event) => { event.preventDefault(); }}>
      {removing ? (
        <p role="status" className="flex items-center gap-1 text-small">
          <Icon name="trash" className="size-4" />
          削除を溜めています。削除を取り消すと編集できます。
        </p>
      ) : null}
      <dl className="grid grid-cols-meta gap-x-2 text-small text-muted-foreground">
        <dt>ID</dt>
        <dd className="font-mono">{adding ? "保存で決まる" : item.id}</dd>
        {adding ? null : (
          <>
            <dt>作成</dt>
            <dd>{item.created === undefined ? "" : formatJst(item.created)}</dd>
            <dt>更新</dt>
            <dd>{`${item.updated === undefined ? "" : formatJst(item.updated)}（${item.updated_by === "user" ? "利用者" : item.updated_by === "external" ? "ほかのセッション" : "AI"}）`}</dd>
          </>
        )}
      </dl>
      {keys.map(({ key: name, input }) =>
        input === "relations" ? (
          <RelationsField key={name} kind={kind} item={item} mark={marks["related"]} removing={removing} index={index} onChange={(related) => { set("related", related); }} />
        ) : input === "options" ? (
          <fieldset key={name} data-key="options" className="flex flex-col gap-2">
            <legend className="text-small font-medium">案</legend>
            {options.map((option) => {
              const removed = removedOptions.includes(option.key);
              return (
                <div key={option.key} data-key={option.key} className={cn("flex flex-col gap-1 rounded-control border border-border-soft p-2", removed && "opacity-60")}>
                  <div className="flex items-center gap-2 text-small">
                    <span aria-hidden="true" className="font-mono font-semibold">
                      {option.key}
                    </span>
                    <label className="inline-flex items-center gap-1">
                      <input type="radio" name={`${item.id}-adopt`} value={option.key} checked={option.adopted === true} disabled={removing || removed} onChange={() => { onChange({ op: "adopt", key: option.key, value: option.key }); }} />
                      採用
                    </label>
                    {marks[option.key] === undefined ? null : <PendingMark kind={marks[option.key] ?? "pending"} compact />}
                    {removed || (adding && option.adopted === true) ? null : (
                      <Button type="button" variant="ghost" size="icon" className="ml-auto" aria-label={`案 ${option.key} を削除`} title={`案 ${option.key} を削除`} disabled={removing} onClick={() => { onChange({ op: "option-remove", key: option.key, value: null }); }}>
                        <Icon name="trash" />
                      </Button>
                    )}
                  </div>
                  <Textarea key={option.content} rows={2} aria-label={`案 ${option.key} の中身`} disabled={removing || removed} defaultValue={option.content} onBlur={(event) => { if (event.target.value !== option.content) onChange({ op: "option-edit", key: option.key, value: { content: event.target.value } }); }} />
                  {blocked[option.key] === undefined ? null : <BlockedNote blocked={blocked[option.key] as BlockedEdit} updated={item.updated ?? null} />}
                </div>
              );
            })}
            {shownDrafts.map((draft) => (
              <div key={draft.key} data-key={draft.key} data-draft="" className="flex flex-col gap-1 rounded-control border border-border-soft p-2">
                <span aria-hidden="true" className="font-mono text-small font-semibold">
                  {draft.key}
                </span>
                <Textarea rows={2} aria-label={`案 ${draft.key} の中身`} disabled={removing} defaultValue={draft.content} onBlur={(event) => { if (event.target.value.trim() !== "") onChange({ op: "option-add", key: draft.key, value: { content: event.target.value } }); }} />
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              disabled={removing}
              className="self-start"
              onClick={() => {
                const symbols = [...options.map((option) => option.key), ...shownDrafts.map((draft) => draft.key)];
                const next = String.fromCharCode(Math.max(64, ...symbols.map((symbol) => symbol.charCodeAt(0))) + 1);
                setDrafts([...drafts, { key: next, content: "" }]);
              }}
            >
              <Icon name="plus" />
              案を追加
            </Button>
          </fieldset>
        ) : (
          <Field key={name} label={labelOf(kind, name)} controlId={`pe-${item.id.replace(/[^A-Za-z0-9]/g, "")}-${name}`} required={name === "title"} mark={marks[name]}>
            {field(name, input)}
            {blocked[name] === undefined ? null : <BlockedNote blocked={blocked[name]} updated={item.updated ?? null} />}
          </Field>
        ),
      )}
      {adding ? null : (
        <section className="flex flex-col gap-1 border-t border-border-soft pt-2">
          <h3 className="m-0 text-h2 font-semibold">項目を削除</h3>
          {removing ? (
            <Button type="button" variant="outline" className="self-start" onClick={onCancelRemove}>
              <Icon name="undo" />
              削除を取り消す
            </Button>
          ) : (
            <Button type="button" variant="destructive" className="self-start" onClick={onRemove}>
              <Icon name="trash" />
              項目を削除
            </Button>
          )}
          {referrers.length === 0 ? null : (
            <p className="flex items-center gap-1 text-small">
              <Icon name="alert" className="size-3" />
              {`${referrers.join("・")} が指しているため、保存のときに削除できません。指している項目から外してください。`}
            </p>
          )}
        </section>
      )}
    </form>
  );
};
