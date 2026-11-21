// 選んだ検討事項のバー。選んだ件数と「推奨の案で決定」を出し、決定できなかった検討事項と理由を並べる
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";

/** 決定できなかった検討事項 1 件 */
export type BulkDecideFailure = { id: string; reason: string };

export type BulkDecideBarProps = {
  /** 選んだ検討事項の件数。0 で失敗も無ければ何も出さない */
  count: number;
  /** 決定している間は真。「推奨の案で決定」を押しても呼ばず、「選択を解除」を押せなくする */
  pending?: boolean;
  /** 直前の決定で決定できなかった検討事項 */
  failures?: BulkDecideFailure[];
  onDecide: () => void;
  onClear: () => void;
};

export const BulkDecideBar = ({ count, pending = false, failures = [], onDecide, onClear }: BulkDecideBarProps) => {
  if (count === 0 && failures.length === 0) return null;
  return (
    <div role="region" aria-label="選んだ検討事項" className="flex flex-wrap items-center gap-2 rounded-card border border-mark-line bg-mark-weak px-2 py-1">
      <span className="text-small">
        <span className="font-mono">{count}</span> 件を選択
      </span>
      {/* 決定中は無効の見た目にせず、文言を読める濃さのまま押しても呼ばない */}
      <Button
        disabled={count === 0}
        aria-disabled={pending ? "true" : undefined}
        aria-busy={pending ? "true" : undefined}
        onClick={() => {
          if (!pending) onDecide();
        }}
      >
        {pending ? <Icon name="spin" className="animate-spin" /> : <Icon name="check" />}
        {pending ? "決定しています" : "推奨の案で決定"}
      </Button>
      <Button variant="ghost" disabled={pending} onClick={onClear}>
        選択を解除
      </Button>
      {failures.length === 0 ? null : (
        <div role="alert" className="flex basis-full items-start gap-1.5 text-small">
          <Icon name="alert" className="mt-0.5 flex-none text-st-review" />
          <div className="min-w-0 flex-1">
            <strong className="block">決定できない検討事項があるため、どの検討事項も決定していません</strong>
            <ul>
              {failures.map((failure) => (
                <li key={failure.id}>
                  <span className="font-mono">{failure.id}</span> {failure.reason}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
