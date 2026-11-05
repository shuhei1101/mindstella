// 書き込めない理由（警告の印と文言）。保存待ちのパネルと編集の入力で使う
import { Icon } from "@/shared/components/icon";
import type { BlockedEdit } from "@/shared/core/edits";
import { formatJst } from "@/shared/core/format";

export type BlockedNoteProps = { blocked: BlockedEdit; updated: string | null; onOpen?: (id: string) => void };

export const BlockedNote = ({ blocked, updated, onOpen }: BlockedNoteProps) => {
  const body = () => {
    if (blocked.reason === "changed" && updated !== null) return `溜めた後の ${formatJst(updated)} に AI がこの項目を書き換えたため、書き込めません。取り消して溜め直してください。`;
    if (blocked.reason !== "referenced" || blocked.refs.length === 0) return blocked.detail;
    return (
      <>
        {blocked.refs.map((ref) =>
          onOpen === undefined ? (
            <span key={ref} className="mr-1 font-mono">
              {ref}
            </span>
          ) : (
            <button key={ref} type="button" className="mr-1 cursor-pointer font-mono underline" onClick={() => { onOpen(ref); }}>
              {ref}
            </button>
          ),
        )}
        が指しているため削除できません。指している項目から外してください。
      </>
    );
  };
  return (
    <p className="m-0 flex items-start gap-1 text-small text-destructive">
      <Icon name="alert" className="size-4 flex-none" />
      <span>{body()}</span>
    </p>
  );
};
