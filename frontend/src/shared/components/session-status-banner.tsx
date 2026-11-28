// MindStella のセッションの状態のバー。トップバーの下に、再起動の途中・再起動の失敗と理由・追加の MCP とプラグインの記録が無いことの警告を出す。自動では閉じない
import type { ReactNode } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";

/** バーに出す状態。`failed` の `retrying` は再起動を依頼してから起動中に戻るまでの間 */
export type SessionStatus =
  | { kind: "running" }
  | { kind: "restarting"; waiting: number }
  | { kind: "failed"; reason: string; retrying: boolean }
  | { kind: "launch_record_missing" };

export type SessionStatusBannerProps = {
  status: SessionStatus;
  onRestart?: () => void;
  onClose?: () => void;
};

/** バーの本文の見出しと文 */
const Body = ({ title, children }: { title: string; children: ReactNode }) => (
  <div className="min-w-0 flex-1 wrap-anywhere">
    {/* eslint-disable-next-line no-restricted-syntax -- 見出しは部品が持つ固定の文言で、記録の文字ではない */}
    <strong className="mb-0.5 block">{title}</strong>
    {children}
  </div>
);

const BAR = "flex items-start gap-2.5 border-b border-border bg-card py-2.5 pl-5 text-small text-foreground max-sm:pl-2.5";

export const SessionStatusBanner = ({ status, onRestart, onClose }: SessionStatusBannerProps) => {
  switch (status.kind) {
    case "running":
      return null;
    case "restarting":
      return (
        <div role="status" className={`${BAR} pr-5 max-sm:pr-2.5`}>
          <Icon name="spin" className="mt-0.5 flex-none animate-spin" />
          <Body title="MindStella のセッションを再起動しています">
            {status.waiting === 0 ? "送信したコメントは、準備ができてから入力します。" : `送信したコメント ${String(status.waiting)} 件は、準備ができてから入力します。`}
          </Body>
        </div>
      );
    case "failed":
      return (
        <div role="alert" className={`${BAR} pr-5 max-sm:pr-2.5`}>
          <Icon name="alert" className="mt-0.5 flex-none text-st-review" />
          <Body title="MindStella のセッションを再起動できませんでした">
            {status.reason}
            <span className="block text-muted-foreground">送信したコメントは保存されていて、再起動した後に入力します。</span>
          </Body>
          <Button variant="outline" className="flex-none whitespace-nowrap" disabled={status.retrying} onClick={onRestart}>
            {status.retrying ? <Icon name="spin" className="animate-spin" /> : null}
            {status.retrying ? "再起動中" : "再起動"}
          </Button>
        </div>
      );
    case "launch_record_missing":
      return (
        <div role="alert" className={`${BAR} pr-1`}>
          <Icon name="alert" className="mt-0.5 flex-none text-st-review" />
          <Body title="追加の MCP とプラグインの記録がありません">
            記録が無いため、追加の MCP とプラグインを付けずに MindStella のセッションを起動しました。コメントは送信できます。追加の MCP とプラグインが要るときは、起動したアプリから再起動してください。
          </Body>
          <Button variant="ghost" size="icon" className="flex-none" aria-label="警告を閉じる" title="警告を閉じる" onClick={onClose}>
            <Icon name="x" />
          </Button>
        </div>
      );
    default: {
      const unknown: never = status;
      return unknown;
    }
  }
};
