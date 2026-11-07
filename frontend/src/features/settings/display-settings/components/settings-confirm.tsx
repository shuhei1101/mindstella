// 既定の保存の確かめの中身（部品設計『既定の保存の確かめ.tsx』）。今の既定と保存する値を並べ、「取り消す」「保存する」を置く
import type { NetworkLook } from "@/shared/api/generated/model";
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { kindsText, lookLabel } from "@/shared/core/display";
import type { Kind } from "@/shared/core/records";

/** 並べる値（見た目と表示する種類） */
export type DisplayValue = { look: NetworkLook; visibleKinds: readonly Kind[] };

export type SettingsConfirmProps = {
  from: DisplayValue;
  to: DisplayValue;
  busy: boolean;
  error: string | null;
  onSave: () => void;
  onCancel: () => void;
};

/** 確かめの 1 行。変える項目は今の既定と保存する値を、変えない項目は今の値と「変えない」を出す */
const ConfirmRow = ({ label, from, to }: { label: string; from: string; to: string }) => (
  <div className="grid gap-0.5">
    <dt className="text-small text-muted-foreground">{label}</dt>
    <dd className="m-0 flex flex-wrap items-center gap-1">
      {from === to ? (
        <>
          <span>{to}</span>
          <span className="rounded-control border border-border px-1.5 text-small">変えない</span>
        </>
      ) : (
        <>
          <span>{from}</span>
          <Icon name="arrow" />
          <span className="font-medium">{to}</span>
        </>
      )}
    </dd>
  </div>
);

export const SettingsConfirm = ({ from, to, busy, error, onSave, onCancel }: SettingsConfirmProps) => {
  return (
    <div className="grid gap-3">
      <p className="m-0 text-small">このワークスペースを開く全員の既定が変わります。表示の設定を自分で変えている人には、変えた項目は当たりません。</p>
      <dl className="m-0 grid gap-2">
        <ConfirmRow label="ネットワークの見た目" from={lookLabel(from.look)} to={lookLabel(to.look)} />
        <ConfirmRow label="表示する種類" from={kindsText(new Set(from.visibleKinds))} to={kindsText(new Set(to.visibleKinds))} />
      </dl>
      {error === null ? null : (
        <div role="alert" className="flex items-start gap-1 text-small text-destructive">
          <Icon name="alert" />
          <span>{error}</span>
        </div>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" autoFocus disabled={busy} onClick={onCancel}>
          取り消す
        </Button>
        <Button disabled={busy} onClick={onSave}>
          {busy ? <Icon name="spin" className="animate-spin" /> : null}
          {busy ? "保存しています" : "保存する"}
        </Button>
      </div>
    </div>
  );
};
