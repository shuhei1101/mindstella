// Ctrl+K（macOS は Cmd+K）で全体の検索を開く。開いている間は `SearchDialog` が受け持つ
import { useShortcut } from "@/shared/hooks/use-shortcut";

export const useSearchShortcut = ({ open, onOpen }: { open: boolean; onOpen: () => void }): void => {
  useShortcut("search.open", onOpen, !open);
};
