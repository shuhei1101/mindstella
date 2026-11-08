// 既定の保存の確かめ（画面設計『既定の保存の確かめ.tsx』）。ワークスペースの既定として保存する前に、今の既定と保存する値を並べるモーダル
import { useState } from "react";

import { SettingsConfirm, type DisplayValue } from "@/features/settings/display-settings/components/settings-confirm";
import { useSaveDisplayDefault } from "@/features/settings/display-settings/use-save-display-default";
import { Dialog, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";
import { AppError } from "@/shared/core/app-error";

export type SettingsConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  from: DisplayValue;
  to: DisplayValue;
  /** 保存した日時（UTC の ISO 8601） */
  onSaved: (at: string) => void;
};

export const SettingsConfirmDialog = ({ open, onOpenChange, from, to, onSaved }: SettingsConfirmDialogProps) => {
  const save = useSaveDisplayDefault();
  const [error, setError] = useState<string | null>(null);
  const busy = save.isPending;
  const handleSave = (): void => {
    setError(null);
    save.mutate(
      { network_look: to.look, visible_kinds: [...to.visibleKinds] },
      {
        onSuccess: () => {
          onSaved(new Date().toISOString());
          onOpenChange(false);
        },
        onError: (reason) => {
          setError(reason instanceof AppError ? `保存できませんでした。${reason.message}` : "保存できませんでした。サーバーが止まっています。立ち上げ直してから保存してください。");
        },
      },
    );
  };
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        // 保存している間は閉じない
        if (!next && busy) return;
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogTitle className="m-0 mb-2 text-h2 font-semibold">ワークスペースの既定を書き換えますか</DialogTitle>
        <SettingsConfirm from={from} to={to} busy={busy} error={error} onSave={handleSave} onCancel={() => { onOpenChange(false); }} />
      </DialogContent>
    </Dialog>
  );
};
