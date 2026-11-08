// 表示の設定の中身（部品設計『表示の設定.tsx』）。表示する種類と差分のミニマップと本文の表とセクションの見せ方を選び、この端末で変えている項目・既定に戻す・ワークスペースの既定にするを出す
import type { NetworkLook } from "@/shared/api/generated/model";
import { Icon, type IconName } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { BODY_VIEW_LABELS, MINIMAP_LABEL } from "@/shared/core/display";
import { KIND_KEYS, KIND_LABEL, type Kind } from "@/shared/core/records";
import type { BodyView } from "@/shared/core/markdown-decorate";

/** パネルの下端に残す知らせ（`ok` は既定にした、`info` は既定が変わった） */
export type SettingsMessage = { kind: "ok" | "info"; text: string };

export type SettingsPanelProps = {
  look: NetworkLook;
  defaultLook: NetworkLook;
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
  /** 「設定を編集する」を押したとき（渡さないと入口を出さない） */
  onWorkspace?: () => void;
};

/** 種類 → 種類の行に出す印 */
const KIND_ICON = { decisions: "decision", tasks: "task", research: "research", docs: "doc", terms: "term", notes: "note", logs: "log" } as const satisfies Record<Kind, IconName>;

const BODY_VIEW_KEYS = ["pin", "head", "stripes", "fold"] as const satisfies readonly (keyof BodyView)[];

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
  const { look, defaultLook, visibleKinds, defaultKinds, counts, overrides, canSave, message, storageAvailable, minimap, bodyView, onKindsChange, onReset, onSaveDefault, onMinimapChange, onBodyViewChange, onWorkspace } = props;
  const shown = KIND_KEYS.filter((kind) => visibleKinds.includes(kind));
  const allShown = shown.length === KIND_KEYS.length;
  const differs = look !== defaultLook || !sameKinds(visibleKinds, defaultKinds);
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
          <AlwaysRow icon="network" label="ネットワーク" />
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
            <p className="m-0 text-small text-muted-foreground">見た目と表示する種類は、ワークスペースの既定と同じです。</p>
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
