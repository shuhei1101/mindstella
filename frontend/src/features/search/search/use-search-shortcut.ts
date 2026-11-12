// Ctrl+K（macOS は Cmd+K）で全体の検索を開く。開いている間は `SearchDialog` が受け持つ
import { useEffect, useRef } from "react";

export const useSearchShortcut = ({ open, onOpen }: { open: boolean; onOpen: () => void }): void => {
  const latest = useRef({ open, onOpen });
  useEffect(() => {
    latest.current = { open, onOpen };
  });
  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      if (latest.current.open || !(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey || event.key.toLowerCase() !== "k") return;
      event.preventDefault();
      latest.current.onOpen();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, []);
};
