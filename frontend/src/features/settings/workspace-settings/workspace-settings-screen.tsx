// 設定の画面（画面設計『設定の画面.tsx』）。ワークスペースの設定をキーごとの入力で書き換え、保存待ちに溜める
import { useRouter } from "@tanstack/react-router";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import { HistoryLimitSchema, usageCount } from "@/features/settings/workspace-settings/form";
import { ChipsInput } from "@/shared/components/chips-input";
import { Icon } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Select } from "@/shared/components/ui/select";
import { Textarea } from "@/shared/components/ui/textarea";
import { pendingMarkOf, SETTINGS_TARGET } from "@/shared/core/edits";
import type { RecordIndex } from "@/shared/core/records";
import { useAddEdit } from "@/shared/hooks/use-edits";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";

const NO_BLOCKED: ReadonlySet<string> = new Set();

type ColumnDef = { key: string; title: string; type: "text" | "url" };

const TABLES: Record<"targets" | "categories" | "links", { label: string; columns: ColumnDef[] }> = {
  targets: { label: "対象", columns: [{ key: "name", title: "名前", type: "text" }, { key: "summary", title: "説明", type: "text" }] },
  categories: { label: "カテゴリー", columns: [{ key: "name", title: "名前", type: "text" }, { key: "target", title: "対象", type: "text" }, { key: "summary", title: "説明", type: "text" }] },
  links: { label: "関連する場所", columns: [{ key: "title", title: "表示名", type: "text" }, { key: "url", title: "URL", type: "url" }] },
};

type Commit = (key: string, value: unknown, map?: Record<string, string>) => void;

/** 使っている値を外したときの付け替え先の選択（選ぶまで溜めない） */
const MoveSelect = ({ removed, count, remaining, onDone }: { removed: string; count: number; remaining: readonly string[]; onDone: (target: string) => void }) => {
  const id = useId();
  return (
    <div data-moving={removed} className="flex flex-col gap-1">
      <label htmlFor={id} className="text-small">{`${removed} を使っている ${String(count)} 件の付け替え先`}</label>
      <Select id={id} defaultValue="" onChange={(event) => { if (event.target.value !== "") onDone(event.target.value); }}>
        <option value="">選んでください</option>
        {remaining.map((entry) => (
          <option key={entry} value={entry}>
            {entry}
          </option>
        ))}
      </Select>
      <p className="m-0 flex items-center gap-1 text-xs">
        <Icon name="alert" className="size-3" />
        付け替え先を選ぶと保存待ちに入ります。
      </p>
    </div>
  );
};

/** 対象・カテゴリー・関連する場所（1 行ずつの表） */
const TableField = ({ settingKey, rows, index, commit }: { settingKey: keyof typeof TABLES; rows: Record<string, string>[]; index: RecordIndex; commit: Commit }) => {
  const { label, columns } = TABLES[settingKey];
  const [moves, setMoves] = useState<{ removed: string; count: number; next: Record<string, string>[] }[]>([]);
  return (
    <div className="flex flex-col gap-1">
      <table aria-label={label} className="w-full text-small">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className="text-left font-medium">
                {column.title}
              </th>
            ))}
            <th>
              <span className="sr-only">操作</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, at) => (
            <tr key={`${String(at)}:${row[columns[0]?.key ?? ""] ?? ""}`}>
              {columns.map((column) => (
                <td key={column.key} className="pr-1">
                  <Input
                    key={row[column.key]}
                    type={column.type}
                    defaultValue={row[column.key] ?? ""}
                    aria-label={`${String(at + 1)} 行目の${column.title}`}
                    onBlur={(event) => {
                      const { value } = event.target;
                      if (value === (row[column.key] ?? "")) return;
                      const next = rows.map((entry, position) => (position === at ? { ...entry, [column.key]: value } : entry));
                      const renamed = column.key === "name" && settingKey !== "links" && row["name"] !== value;
                      commit(settingKey, next, renamed ? { [row["name"] ?? ""]: value } : undefined);
                    }}
                  />
                </td>
              ))}
              <td>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`${String(at + 1)} 行目を削除`}
                  onClick={() => {
                    const next = rows.filter((_, position) => position !== at);
                    const removed = row["name"] ?? "";
                    const used = settingKey === "links" ? 0 : usageCount(index, settingKey, removed);
                    if (used === 0) commit(settingKey, next);
                    else setMoves([...moves.filter((move) => move.removed !== removed), { removed, count: used, next }]);
                  }}
                >
                  <Icon name="trash" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {moves.map(({ removed, count, next }) => (
        <MoveSelect key={removed} removed={removed} count={count} remaining={next.map((entry) => entry["name"] ?? "")} onDone={(target) => { commit(settingKey, next, { [removed]: target }); setMoves(moves.filter((move) => move.removed !== removed)); }} />
      ))}
      <Button variant="outline" className="self-start" onClick={() => { commit(settingKey, [...rows, Object.fromEntries(columns.map((column) => [column.key, ""]))]); }}>
        <Icon name="plus" />
        {`${label}を追加`}
      </Button>
    </div>
  );
};

const ChipsField = ({ settingKey, name, values, index, commit }: { settingKey: "playbooks" | "phases"; name: string; values: string[]; index: RecordIndex; commit: Commit }) => {
  const [moves, setMoves] = useState<{ removed: string; count: number; next: string[] }[]>([]);
  return (
    <>
      <ChipsInput
        controlId={`pe-ws-${settingKey}`}
        name={name}
        hint={`${name}を入れる`}
        values={values}
        onChange={(next, removed) => {
          const names = next as string[];
          const used = removed !== null && settingKey !== "playbooks" ? usageCount(index, settingKey, removed) : 0;
          if (removed === null || used === 0) commit(settingKey, names);
          else setMoves([...moves.filter((move) => move.removed !== removed), { removed, count: used, next: names }]);
        }}
      />
      {moves.map(({ removed, count, next }) => (
        <MoveSelect key={removed} removed={removed} count={count} remaining={next} onDone={(target) => { commit(settingKey, next, { [removed]: target }); setMoves(moves.filter((move) => move.removed !== removed)); }} />
      ))}
    </>
  );
};

export const WorkspaceSettingsScreen = () => {
  const { setTab } = usePreviewSearch();
  const router = useRouter();
  const { index, edits } = useRecords();
  // 開いたとき（記録を読み終えて描いたとき）に見出しへフォーカスを移す
  const heading = useRef<HTMLHeadingElement>(null);
  const loaded = index !== null;
  useEffect(() => {
    if (loaded) heading.current?.focus();
  }, [loaded]);
  const add = useAddEdit();
  const [error, setError] = useState<string | null>(null);
  if (index === null) return null;
  const { settings } = index.data;
  const commit: Commit = (key, value, map) => {
    setError(null);
    add.mutate({ op: "setting", target: SETTINGS_TARGET, key, value, ...(map === undefined ? {} : { map }) }, { onError: (failure) => { setError(failure.message); } });
  };
  const field = (key: string, name: string, children: ReactNode, controlId?: string) => {
    const mark = pendingMarkOf({ edits, blocked: NO_BLOCKED, target: SETTINGS_TARGET, key });
    return (
      <div data-key={key} className="flex flex-col gap-1">
        <div className="flex items-center gap-1 text-small font-medium">
          {controlId === undefined ? <span>{name}</span> : <label htmlFor={controlId}>{name}</label>}
          {mark === null ? null : <PendingMark kind={mark} compact />}
        </div>
        {children}
      </div>
    );
  };
  const text = (key: string, name: string, value: string | undefined) =>
    field(key, name, <Input key={value} id={`pe-ws-${key}`} type="text" defaultValue={value ?? ""} autoComplete="off" onBlur={(event) => { if (event.target.value !== (value ?? "")) commit(key, event.target.value); }} />, `pe-ws-${key}`);
  const goal = settings.goal ?? { phase: settings.phases[0] ?? "", summary: "", deliverables: [] };
  const record = settings as unknown as Record<string, unknown>;
  const rowsOf = (key: string) => (record[key] ?? []) as Record<string, string>[];
  return (
    <main id="main" className="min-h-0 flex-1 overflow-y-auto p-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <div className="flex items-center gap-2">
          <h1 ref={heading} tabIndex={-1} className="m-0 text-next font-semibold">設定</h1>
          {/* 開く前の画面に戻る。URL で直に開いたときは概要を開く */}
          <Button variant="outline" className="ml-auto" onClick={() => { if (router.history.canGoBack()) router.history.back(); else setTab("overview"); }}>
            <Icon name="x" />
            閉じる
          </Button>
        </div>
        <form noValidate aria-label="ワークスペースの設定" className="flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); }}>
          <fieldset className="flex flex-col gap-3">
            <legend className="font-medium">話し合い</legend>
            {text("summary", "題名", settings.summary)}
            {field("description", "説明", <Textarea key={settings.description} id="pe-ws-description" rows={2} defaultValue={settings.description ?? ""} onBlur={(event) => { if (event.target.value !== (settings.description ?? "")) commit("description", event.target.value === "" ? null : event.target.value); }} />, "pe-ws-description")}
            {field("playbooks", "プレイブック", <ChipsField settingKey="playbooks" name="プレイブック" values={settings.playbooks ?? []} index={index} commit={commit} />)}
            {field(
              "goal",
              "ゴール",
              <>
                <label htmlFor="pe-ws-goal-phase" className="text-small">
                  届けるフェーズ
                </label>
                <Select id="pe-ws-goal-phase" value={goal.phase} onChange={(event) => { commit("goal", { ...goal, phase: event.target.value }); }}>
                    {settings.phases.map((entry) => (
                      <option key={entry} value={entry}>
                        {entry}
                      </option>
                    ))}
                </Select>
                <label htmlFor="pe-ws-goal-summary" className="text-small">
                  ゴールの中身
                </label>
                <Textarea key={goal.summary} id="pe-ws-goal-summary" rows={2} defaultValue={goal.summary} onBlur={(event) => { if (event.target.value !== goal.summary) commit("goal", { ...goal, summary: event.target.value }); }} />
                <div className="text-small">
                  納品物
                  <ul>
                    {goal.deliverables.map((entry) => (
                      <li key={entry.title}>
                        {entry.doc === undefined ? null : <span className="mr-1 font-mono text-xs">{entry.doc}</span>}
                        {entry.title}
                      </li>
                    ))}
                  </ul>
                </div>
              </>,
            )}
          </fieldset>
          <fieldset className="flex flex-col gap-3">
            <legend className="font-medium">進め方</legend>
            {field("phases", "フェーズ", <ChipsField settingKey="phases" name="フェーズ" values={settings.phases} index={index} commit={commit} />)}
            {text("target_label", "最上位の軸の呼び名", settings.target_label)}
            {field("targets", "対象", <TableField settingKey="targets" rows={rowsOf("targets")} index={index} commit={commit} />)}
            {field("categories", "カテゴリー", <TableField settingKey="categories" rows={rowsOf("categories")} index={index} commit={commit} />)}
          </fieldset>
          <fieldset className="flex flex-col gap-3">
            <legend className="font-medium">関連</legend>
            {field("links", "関連する場所", <TableField settingKey="links" rows={rowsOf("links")} index={index} commit={commit} />)}
          </fieldset>
          <fieldset className="flex flex-col gap-3">
            <legend className="font-medium">変更履歴</legend>
            {field(
              "history_limit",
              "保持する回数",
              <>
                <Input
                  key={settings.history_limit}
                  id="pe-ws-history_limit"
                  type="number"
                  min={1}
                  step={1}
                  inputMode="numeric"
                  className="w-32"
                  defaultValue={settings.history_limit ?? ""}
                  onBlur={(event) => {
                    const parsed = HistoryLimitSchema.safeParse(event.target.value === "" ? undefined : event.target.value);
                    if (parsed.success && parsed.data !== settings.history_limit) commit("history_limit", parsed.data);
                  }}
                />
                <p className="m-0 text-xs text-muted-foreground">変更履歴に残す書き換えのまとまりの数です。</p>
              </>,
              "pe-ws-history_limit",
            )}
          </fieldset>
          {error === null ? null : (
            <p role="alert" className="flex items-center gap-1 text-small text-destructive">
              <Icon name="alert" className="size-4" />
              {error}
            </p>
          )}
        </form>
      </div>
    </main>
  );
};
