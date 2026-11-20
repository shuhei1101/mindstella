// 確認済みの切り替え。文言は「確認済み」のまま、チェックと色で状態を示す。押すと確認済みにし、もう一度押すと解除する。狭い幅ではアイコンだけにする
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/cn";

export type ConfirmedToggleProps = {
  confirmed: boolean;
  /** 書き込みの応答を待っている間は押せない */
  saving?: boolean;
  onToggle: () => void;
};

export const ConfirmedToggle = ({ confirmed, saving = false, onToggle }: ConfirmedToggleProps) => {
  const title = confirmed ? "確認済みを解除する" : "確認済みにする";
  return (
    <Button variant="outline" aria-pressed={confirmed} title={title} disabled={saving} className={cn(confirmed && "border-st-done text-st-done")} onClick={onToggle}>
      <Icon name={confirmed ? "checked" : "unchecked"} />
      <span className="max-sm:sr-only">確認済み</span>
    </Button>
  );
};
