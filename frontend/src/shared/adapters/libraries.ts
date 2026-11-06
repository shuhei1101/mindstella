// 描画のライブラリ（mdmark・mermaid・elkjs・marked・jsdiff）を、今の画面と同じ配信元と版から `integrity` で確かめて読む（インターフェース定義『SPAを開く』の制約「描画のライブラリ」）
import { useSyncExternalStore } from "react";

const MDMARK_BASE = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark@v0.8.0/dist";

/** mdmark の JavaScript */
export const MDMARK_JS = { url: `${MDMARK_BASE}/index.js`, integrity: "sha384-TM6o/p3o+qWHh5HK5iGMRN6krIdz4rxapjSgvX1yJhY9z7eHJl2WGBaiJAiZIAoq" };

/** mdmark の CSS */
export const MDMARK_CSS = { url: `${MDMARK_BASE}/index.css`, integrity: "sha384-3lS+93C5w5loNr+EKJlqTfbAHmBGx+GCkqJiqOGUFFaA56e87waceMQ1TMY94wcV" };

/** script 要素で読むライブラリの URL・integrity と、読めたときに置かれるグローバルの名前 */
export const LIBRARIES = {
  marked: { url: "https://cdn.jsdelivr.net/npm/marked@18.0.14/lib/marked.umd.js", integrity: "sha384-2vpGtuKqJvFlwJqYnf/wUMuzUfhUnYBt9oay0e2yaFcq0Dh6/aEbQ8YAOeKGzlYo", global: "marked" },
  elkjs: { url: "https://cdn.jsdelivr.net/npm/elkjs@0.12.0/lib/elk.bundled.js", integrity: "sha384-ww57TDqx4cGknIavPm0QKO+aygLUR1BLSn2Vhbnt1XdYKWcwLyWTFKX7aZMaKIi2", global: "ELK" },
  mermaid: { url: "https://cdn.jsdelivr.net/npm/mermaid@12.1.0/dist/mermaid.min.js", integrity: "sha384-EbBpjO7rlR6eqZEcG7GaPpyk9H9WrMyPWX4d3KvPYltgt8Z8l0z6R56B1qP40pR4", global: "mermaid" },
  jsdiff: { url: "https://cdn.jsdelivr.net/npm/diff@9.0.0/dist/diff.min.js", integrity: "sha384-TvJwlBkfFFd9hmaVfyJyF6lIPjAUL6x01MvObCeUao5yP6QZ6owU6fqw+JQoyRD1", global: "Diff" },
} as const;

/** ライブラリの名前 */
export type LibraryName = keyof typeof LIBRARIES | "mdmark";

/** 読み込みの状態 */
export type LibraryStatus = "loading" | "ready" | "failed";

/** hook が返す状態 */
export type LibraryState = { status: LibraryStatus; library: unknown };

const loading = new Map<LibraryName, Promise<unknown>>();
const loaded = new Map<LibraryName, unknown>();
const failed = new Set<LibraryName>();
const listeners = new Set<() => void>();

const notify = (): void => {
  for (const listener of listeners) listener();
};

/** script 要素で読み、置かれたグローバルを返す */
const loadScript = (name: keyof typeof LIBRARIES): Promise<unknown> =>
  new Promise((resolve, reject) => {
    const { url, integrity, global } = LIBRARIES[name];
    const script = document.createElement("script");
    script.src = url;
    script.integrity = integrity;
    script.crossOrigin = "anonymous";
    script.addEventListener("load", () => {
      resolve(Reflect.get(window, global));
    });
    script.addEventListener("error", () => {
      reject(new Error(url));
    });
    document.head.appendChild(script);
  });

/** mdmark の CSS を link で読み、JavaScript を import map の integrity で確かめて読む */
const loadMdmark = async (): Promise<unknown> => {
  if (document.querySelector(`link[href="${MDMARK_CSS.url}"]`) === null) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = MDMARK_CSS.url;
    link.integrity = MDMARK_CSS.integrity;
    link.crossOrigin = "anonymous";
    document.head.appendChild(link);
  }
  return (await import(/* @vite-ignore */ MDMARK_JS.url)) as unknown;
};

/** 1 つのライブラリを 1 度だけ読み、結果を返す。読めなかったら代わりを読まず null を返す */
export const loadLibrary = (name: LibraryName): Promise<unknown> => {
  const started = loading.get(name);
  if (started !== undefined) return started;
  const promise = (name === "mdmark" ? loadMdmark() : loadScript(name))
    .then((library) => {
      if (library === undefined) throw new Error(name);
      loaded.set(name, library);
      notify();
      return library;
    })
    .catch(() => {
      failed.add(name);
      notify();
      return null;
    });
  loading.set(name, promise);
  return promise;
};

/** 読めたライブラリを返す。読めていなければ null */
export const getLibrary = (name: LibraryName): unknown => loaded.get(name) ?? null;

/** 読み込みの状態を返す */
export const libraryState = (name: LibraryName): LibraryStatus => {
  if (loaded.has(name)) return "ready";
  return failed.has(name) ? "failed" : "loading";
};

const subscribe = (listener: () => void): (() => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

/** ライブラリを読み始め、読み込みの状態を返す */
export const useLibrary = (name: LibraryName): LibraryState => {
  void loadLibrary(name);
  const status = useSyncExternalStore(subscribe, () => libraryState(name));
  // React Compiler が取得を覚えないよう、状態で分ける
  return { status, library: status === "ready" ? getLibrary(name) : null };
};

/** テストの間で読み込みの状態を消す */
export const resetLibrariesForTest = (): void => {
  loading.clear();
  loaded.clear();
  failed.clear();
};
