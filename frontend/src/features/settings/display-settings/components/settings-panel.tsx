// 表示の設定の中身（部品設計『表示の設定.tsx』）。表示する種類と差分のミニマップと本文の表とセクションの見せ方と「レビューに追加」の後のフォーカスを選び、この端末で変えている項目・既定に戻す・ワークスペースの既定にするを出す
import { useId } from "react";

import { Icon, type IconName } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { BODY_VIEW_LABELS, FOCUS_AFTER_ADD_LABEL, MINIMAP_LABEL } from "@/shared/core/display";
import { KIND_KEYS, KIND_LABEL, type Kind } from "@/shared/core/records";
import type { BodyView } from "@/shared/core/markdown-decorate";

/** パネルの下端に残す知らせ（`ok` は既定にした、`info` は既定が変わった） */
export type SettingsMessage = { kind: "ok" | "info"; text: string };

/** 「レビューに追加」の後のフォーカスの選び（`auto` は端末の主な入力で決める） */
export type FocusAfterAdd = "auto" | "input" | "none";

/** 「レビューに追加」の後のフォーカスの選択肢（値・名前） */
const FOCUS_AFTER_ADD_OPTIONS = [
  { key: "auto", label: "自動" },
  { key: "input", label: "入力欄へ戻す" },
  { key: "none", label: "戻さない" },
] as const satisfies readonly { key: FocusAfterAdd; label: string }[];

export type SettingsPanelProps = {
  visibleKinds: readonly Kind[];
  defaultKinds: readonly Kind[];
  counts: Partial<Record<Kind, number>>;
  overrides: readonly string[];
  canSave: boolean;
  message: SettingsMessage | null;
  storageAvailable: boolean;
  minimap: boolean;
  bodyView: BodyView;
  onKindsChange: (kinds: Kind[]) => void;
  onReset: () => void;
  onSaveDefault: () => void;
  onClose: () => void;
  onMinimapChange: (shown: boolean) => void;
  onBodyViewChange: (key: keyof BodyView, value: boolean) => void;
  /** 当てている「レビューに追加」の後のフォーカス（「ワークスペースの既定にする」を出すかの比べには使わない） */
  focusAfterAdd: FocusAfterAdd;
  /** 端末の主な入力がタッチか（「自動」の下の文を切り替える） */
  pointerCoarse: boolean;
  onFocusAfterAddChange: (value: FocusAfterAdd) => void;
  /** 修飾キーの無い 1 文字のショートカット（一覧の並びの前後の `j`・`k`）を使用するか */
  singleKeyShortcuts?: boolean;
  onSingleKeyShortcutsChange?: (value: boolean) => void;
  /** 「設定を編集する」を押したとき（渡さないと入口を出さない） */
  onWorkspace?: () => void;
};

/** 区画「キーボード」のチェックの文言 */
const SINGLE_KEY_SHORTCUTS_CHECK_LABEL = "1 文字のショートカットを使用する";

/** 種類 → 種類の行に出す印 */
const KIND_ICON = { decisions: "decision", tasks: "task", research: "research", docs: "doc", terms: "term", notes: "note", logs: "log" } as const satisfies Record<Kind, IconName>;

const BODY_VIEW_KEYS = ["fold"] as const satisfies readonly (keyof BodyView)[];

/** 2 つの並びが同じ要素を持つか */
const sameKinds = (a: readonly Kind[], b: readonly Kind[]): boolean => a.length === b.length && a.every((kind) => b.includes(kind));

const AlwaysRow = ({ icon, label }: { icon: IconName; label: string }) => (
  <li data-part="always" className="flex min-h-10 items-center gap-2 text-muted-foreground">
    <Icon name="check" />
    <Icon name={icon} />
    <span className="flex-1">{label}</span>
    <span className="text-small">常に表示</span>
  </li>
);

export const SettingsPanel = (props: SettingsPanelProps) => {
  const { visibleKinds, defaultKinds, counts, overrides, canSave, message, storageAvailable, minimap, bodyView, focusAfterAdd, pointerCoarse, singleKeyShortcuts, onSingleKeyShortcutsChange, onKindsChange, onReset, onSaveDefault, onMinimapChange, onBodyViewChange, onFocusAfterAddChange, onWorkspace } = props;
  const focusHintId = useId();
  const keyHintId = useId();
  const usesSingleKey = singleKeyShortcuts ?? true;
  const shown = KIND_KEYS.filter((kind) => visibleKinds.includes(kind));
  const allShown = shown.length === KIND_KEYS.length;
  const differs = !sameKinds(visibleKinds, defaultKinds);
  const toggleKind = (kind: Kind): void => {
    onKindsChange(KIND_KEYS.filter((one) => (one === kind ? !visibleKinds.includes(one) : visibleKinds.includes(one))));
  };
  return (
    <div data-part="wrap" className="grid gap-4">
      {storageAvailable ? null : (
        <p role="alert" data-part="note" className="m-0 flex items-start gap-1 text-small">
          <Icon name="alert" />
          <span>この端末に保存できません。選んだ表示は、このページを開いている間だけ当たります。</span>
        </p>
      )}
      <fieldset data-part="kinds" className="m-0 grid gap-1 border-0 p-0">
        <legend className="mb-1 font-medium">表示する種類</legend>
        <ul className="m-0 grid list-none gap-1 p-0">
          <li data-part="all">
            <label className="flex min-h-10 items-center gap-2">
              <Checkbox checked={allShown} ref={(element) => {
                if (element !== null) element.indeterminate = shown.length > 0 && !allShown;
              }} onChange={() => onKindsChange(allShown ? [] : [...KIND_KEYS])} />
              <span className="flex-1">すべて</span>
              <span data-part="count" className="font-mono text-small">{`${String(shown.length)}/${String(KIND_KEYS.length)}`}</span>
            </label>
          </li>
          <AlwaysRow icon="home" label="概要" />
          {KIND_KEYS.map((kind) => (
            <li key={kind} data-part="kind">
              <label className="flex min-h-10 items-center gap-2">
                <Checkbox value={kind} checked={visibleKinds.includes(kind)} onChange={() => toggleKind(kind)} />
                <Icon name={KIND_ICON[kind]} />
                <span data-part="label" className="flex-1">{KIND_LABEL[kind]}</span>
                <span data-part="count" className="font-mono text-small">{counts[kind] ?? ""}</span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>
      <fieldset className="m-0 grid gap-1 border-0 p-0">
        <legend className="mb-1 font-medium">詳細に表示するもの</legend>
        <ul className="m-0 grid list-none gap-1 p-0">
          <li>
            <label className="flex min-h-10 items-center gap-2">
              <Checkbox checked={minimap} onChange={() => onMinimapChange(!minimap)} />
              <span>{MINIMAP_LABEL}</span>
            </label>
          </li>
          {BODY_VIEW_KEYS.map((key) => (
            <li key={key}>
              <label className="flex min-h-10 items-center gap-2">
                <Checkbox checked={bodyView[key]} onChange={() => onBodyViewChange(key, !bodyView[key])} />
                <span>{BODY_VIEW_LABELS[key]}</span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>
      <fieldset className="m-0 grid gap-1 border-0 p-0">
        <legend className="mb-1 font-medium">コメントの入力</legend>
        <fieldset className="m-0 grid gap-1 border-0 p-0" aria-describedby={focusHintId}>
          <legend className="mb-1">{FOCUS_AFTER_ADD_LABEL}</legend>
          <ul className="m-0 grid list-none gap-1 p-0">
            {FOCUS_AFTER_ADD_OPTIONS.map(({ key, label }) => (
              <li key={key}>
                <label className="flex min-h-10 items-center gap-2">
                  <input type="radio" name="focus-after-add" value={key} checked={focusAfterAdd === key} className="size-4 accent-primary" onChange={() => onFocusAfterAddChange(key)} />
                  <span className="grid">
                    <span>{label}</span>
                    {key === "auto" ? <span className="text-small text-muted-foreground">{pointerCoarse ? "この端末では戻しません" : "この端末では入力欄へ戻します"}</span> : null}
                  </span>
                </label>
              </li>
            ))}
          </ul>
          <p id={focusHintId} className="m-0 text-small text-muted-foreground">自動は、マウスで操作する端末では入力欄へ戻し、タッチで操作する端末では戻しません。</p>
        </fieldset>
      </fieldset>
      <fieldset className="m-0 grid gap-1 border-0 p-0">
        <legend className="mb-1 font-medium">キーボード</legend>
        <ul className="m-0 grid list-none gap-1 p-0">
          <li>
            <label className="flex min-h-10 items-center gap-2">
              <Checkbox checked={usesSingleKey} aria-describedby={keyHintId} onChange={() => onSingleKeyShortcutsChange?.(!usesSingleKey)} />
              <span>{SINGLE_KEY_SHORTCUTS_CHECK_LABEL}</span>
            </label>
          </li>
        </ul>
        <p id={keyHintId} className="m-0 text-small text-muted-foreground">オフにすると、詳細の j・k で一覧の前後の項目へ移る操作を受け付けません。</p>
      </fieldset>
      <div className="grid gap-2">
        {overrides.length === 0 ? (
          <p className="m-0 text-small text-muted-foreground">ワークスペースの既定のまま表示しています。</p>
        ) : (
          <>
            <p data-part="over" className="m-0 grid gap-0.5 text-small">
              <span data-part="over-heading" className="font-medium">この端末で変えている項目</span>
              <span>{overrides.join("・")}</span>
            </p>
            <Button variant="outline" className="justify-self-start" onClick={onReset}>
              <Icon name="undo" />
              既定に戻す
            </Button>
          </>
        )}
      </div>
      {canSave ? (
        <div data-part="save" className="grid gap-2 border-t border-border pt-3">
          {differs ? (
            <Button variant="outline" className="justify-self-start" aria-haspopup="dialog" onClick={onSaveDefault}>
              <Icon name="save" />
              ワークスペースの既定にする
            </Button>
          ) : (
            <p className="m-0 text-small text-muted-foreground">表示する種類は、ワークスペースの既定と同じです。</p>
          )}
        </div>
      ) : null}
      <p role="status" data-part="message" data-kind={message?.kind} className="m-0 flex items-start gap-1 text-small">
        {message === null ? null : (
          <>
            <Icon name={message.kind === "ok" ? "check" : "sliders"} />
            <span>{message.text}</span>
          </>
        )}
      </p>
      {onWorkspace === undefined ? null : (
        <div className="grid gap-1 border-t border-border pt-3">
          <h3 className="m-0 text-body font-medium">ワークスペースの設定</h3>
          <p className="m-0 text-small text-muted-foreground">題名・フェーズ・ゴール・対象・カテゴリー</p>
          <Button variant="outline" className="justify-self-start" onClick={onWorkspace}>
            <Icon name="edit" />
            設定を編集する
          </Button>
        </div>
      )}
    </div>
  );
};
