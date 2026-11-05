// 描画のライブラリの差し替え。mdmark は Markdown をそのまま HTML として入れ、marked と jsdiff は本物を使う
import * as jsdiff from "diff";
import { marked } from "marked";

import type { LibraryName, LibraryState } from "@/shared/adapters/libraries";

const mdmark = {
  mount: (root: HTMLElement, { markdown }: { markdown: string }) => {
    root.innerHTML = markdown;
    return { destroy: () => undefined };
  },
};

const LOADED: Partial<Record<LibraryName, unknown>> = { mdmark, jsdiff, marked };

export const getLibrary = (name: LibraryName): unknown => LOADED[name] ?? null;
export const libraryState = (name: LibraryName): LibraryState["status"] => (name in LOADED ? "ready" : "failed");
export const useLibrary = (name: LibraryName): LibraryState => ({ status: libraryState(name), library: getLibrary(name) });
