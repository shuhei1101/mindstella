// 変更履歴のモーダル（部品設計『変更履歴.tsx』）。差分の表示で比べる時点を、日時・説明・変わった項目の数つきで新しい順に並べ、1 つ選ばせる
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";

/** モーダルに並べる時点 1 つ */
export type HistoryPoint = { sel: string; name: string; sub: string; count?: number };

export type HistoryDialogProps = {
  points: HistoryPoint[];
  current: string;
  onSelect: (sel: string) => void;
  onClose: () => void;
};

export const HistoryDialog = ({ points, current, onSelect, onClose }: HistoryDialogProps) => (
  <Dialog
    open
    onOpenChange={(open) => {
      if (!open) onClose();
    }}
  >
    <DialogContent>
      <div className="flex items-center justify-between border-b border-border-soft p-3">
        <DialogTitle className="text-h2 font-medium">変更履歴</DialogTitle>
        <DialogClose render={<Button variant="ghost" size="icon" aria-label="変更履歴を閉じる" />}>
          <Icon name="x" />
        </DialogClose>
      </div>
      <ul className="max-h-96 overflow-auto p-1">
        {points.map((point) => {
          const selected = point.sel === current;
          return (
            <li key={point.sel}>
              <button
                type="button"
                data-sel={point.sel}
                aria-current={selected ? "true" : undefined}
                onClick={() => {
                  onSelect(point.sel);
                  onClose();
                }}
                className="flex w-full cursor-pointer items-center gap-2 rounded-control p-2 text-left hover:bg-accent"
              >
                <span aria-hidden="true" className="w-4 flex-none">
                  {selected ? <Icon name="check" /> : null}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-small font-medium">{point.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">{point.sub}</span>
                </span>
                {point.count === undefined ? null : <span className="font-mono text-xs text-muted-foreground">{point.count} 件</span>}
              </button>
            </li>
          );
        })}
      </ul>
    </DialogContent>
  </Dialog>
);
