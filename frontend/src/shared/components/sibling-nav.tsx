// 元の画面の今の並びで、前後の項目へ移るボタンと並びの中の位置（詳細パネル・詳細の全画面の見出しに置く）
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";

export type SiblingNavProps = {
  /** 並びの中の今の項目の位置（1 始まり） */
  position: number;
  /** 並びの件数 */
  total: number;
  onPrev: () => void;
  onNext: () => void;
};

export const SiblingNav = ({ position, total, onPrev, onNext }: SiblingNavProps) => (
  <div role="group" aria-label="一覧の並び" className="flex flex-none items-center rounded-control border border-border-soft">
    <Button variant="ghost" size="icon" aria-label="一覧の前の項目" title="一覧の前の項目" disabled={position <= 1} onClick={onPrev}>
      <Icon name="chev" className="-rotate-90" />
    </Button>
    <span className="min-w-12 text-center font-mono text-xs whitespace-nowrap text-muted-foreground">
      {position} / {total}
    </span>
    <Button variant="ghost" size="icon" aria-label="一覧の次の項目" title="一覧の次の項目" disabled={position >= total} onClick={onNext}>
      <Icon name="chev" className="rotate-90" />
    </Button>
  </div>
);
