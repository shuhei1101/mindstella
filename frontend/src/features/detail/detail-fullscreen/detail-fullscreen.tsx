// 詳細の全画面（画面設計『詳細の全画面.tsx』）。詳細パネルの中身を中央のモーダルで大きく出す
import { DetailContent } from "@/features/detail/detail-panel/detail-panel";
import { Dialog, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";
import type { RecordIndex } from "@/shared/core/records";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";

export type DetailFullscreenProps = { id: string; index: RecordIndex };

export const DetailFullscreen = ({ id, index }: DetailFullscreenProps) => {
  const { setFull } = usePreviewSearch();
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) setFull(false);
      }}
    >
      <DialogContent className="flex h-full max-w-5xl flex-col rounded-none border-0 p-0 shadow-none">
        <DialogTitle className="sr-only">{index.byId.get(id)?.item.title}</DialogTitle>
        <DetailContent key={id} id={id} index={index} full />
      </DialogContent>
    </Dialog>
  );
};
