// 描画のライブラリ（mdmark・mermaid・marked・jsdiff）を読む。mdmark は『記録の取得』の `mdmark_ref` から `integrity` なしで、それ以外はプラグインの libraries.json の URL から `integrity` で確かめて読む。配る書き出しは HTML が中に持つ配布ファイルを読む
import { useSyncExternalStore } from "react";

import libraryRows from "../../../../plugins/mindstella/skills/mindmap/preview/libraries.json";

/** jsDelivr の mdmark の `dist/` の URL の形（`{ref}` に『記録の取得』の `mdmark_ref`。受ける前は `develop`） */
export const MDMARK_CDN_BASE = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark@{ref}/dist";

/** ref を受ける前（前の版の配信が `mdmark_ref` を返さないときも）に読む mdmark のブランチ */
const MDMARK_FALLBACK_REF = "develop";

/** mdmark の `mount` の `config.map`（mdmark の設定の `map` と同じ形） */
export type MdmarkMapConfig = Record<string, unknown>;

/** 『記録の取得』の `settings.mdmark` */
export type MdmarkSettings = { version?: string; map?: MdmarkMapConfig };

let mdmarkRef = MDMARK_FALLBACK_REF;
let mdmarkMap: MdmarkMapConfig | undefined;

/** 『記録の取得』の `settings.mdmark` と `mdmark_ref` を受け取り、mdmark を読む URL（`mdmark_ref`。無ければ `develop`）と `mount` に指定する `map` を決める。読み始めた後に違う ref を受けたら、次に開いた画面から使う */
export const setMdmarkSettings = (settings: MdmarkSettings | undefined, ref: string | undefined): void => {
  mdmarkRef = ref ?? MDMARK_FALLBACK_REF;
  mdmarkMap = settings?.map;
};

/** `setMdmarkSettings` で決めた mdmark の JavaScript と CSS の URL を返す（ref を受けていなければ `develop`） */
export const mdmarkUrls = (): { js: string; css: string } => {
  const base = MDMARK_CDN_BASE.replace("{ref}", mdmarkRef);
  return { js: `${base}/index.js`, css: `${base}/index.css` };
};

/** `setMdmarkSettings` で受けた `map`（`mount` の `config.map` に渡す）を返す */
export const mdmarkMapConfig = (): MdmarkMapConfig | undefined => mdmarkMap;

/** URL の ES モジュールを読む関数（単体テストで差し替える） */
type ImportModule = (url: string) => Promise<unknown>;

const importByUrl: ImportModule = (url) => import(/* @vite-ignore */ url) as Promise<unknown>;
let importModule: ImportModule = importByUrl;

/** script 要素で読むライブラリの名前 */
type ScriptLibraryName = "marked" | "mermaid" | "jsdiff";

/** libraries.json の package と、画面が引くライブラリの名前の対応 */
const PACKAGE_NAMES = { marked: "marked", mermaid: "mermaid", diff: "jsdiff" } as const satisfies Record<string, ScriptLibraryName>;

/** libraries.json の 1 行 */
type LibraryRow = { package: string; url: string; integrity: string; global: string };

/** script 要素で読むライブラリの URL・integrity と、読めたときに置かれるグローバルの名前（プラグインの libraries.json を名前で引ける形にしたもの） */
export const LIBRARIES = Object.fromEntries(
  (libraryRows as LibraryRow[]).map((row) => [PACKAGE_NAMES[row.package as keyof typeof PACKAGE_NAMES], { url: row.url, integrity: row.integrity, global: row.global }]),
) as Record<ScriptLibraryName, { url: string; integrity: string; global: string }>;

/** ライブラリの名前 */
export type LibraryName = ScriptLibraryName | "mdmark";

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

/** script 要素で読み、置かれたグローバルを返す。グローバルが既にあれば（配る書き出しの中身を持つ script 要素が置いたもの）それを返す */
const loadScript = (name: ScriptLibraryName): Promise<unknown> =>
  new Promise((resolve, reject) => {
    const { url, integrity, global } = LIBRARIES[name];
    const present: unknown = Reflect.get(window, global);
    if (present !== undefined) {
      resolve(present);
      return;
    }
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

/** 配る書き出しが mdmark の本体と部品の中身を持つ要素の ID の頭（部品は `-{部品の名前}` を付ける） */
const MDMARK_EMBEDDED_ID = "mindmap-mdmark";

/** mdmark の部品の名前 */
const MDMARK_PART_NAMES = ["map", "view", "comments"] as const;

/** 中身の文字を Blob の URL にして import() する */
const importText = async (text: string): Promise<unknown> => {
  const url = URL.createObjectURL(new Blob([text], { type: "text/javascript" }));
  try {
    return await importModule(url);
  } finally {
    URL.revokeObjectURL(url);
  }
};

/** 配る書き出しの、中身を持つ mdmark を読み、部品の読み込みを中身へ差し替える */
const loadEmbeddedMdmark = async (embedded: Element): Promise<unknown> => {
  const library = (await importText(embedded.textContent ?? "")) as { setPartModuleLoader?: (name: string, load: () => Promise<unknown>) => void };
  for (const name of MDMARK_PART_NAMES) {
    const part = document.getElementById(`${MDMARK_EMBEDDED_ID}-${name}`);
    if (part === null || library.setPartModuleLoader === undefined) continue;
    const text = part.textContent ?? "";
    library.setPartModuleLoader(name, () => importText(text));
  }
  return library;
};

/** 設定のバージョンの mdmark の CSS を link で読み、JavaScript を `integrity` なしで読む。配る書き出しは中身を持つ mdmark を読む */
const loadMdmark = async (): Promise<unknown> => {
  const embedded = document.getElementById(MDMARK_EMBEDDED_ID);
  if (embedded !== null) return await loadEmbeddedMdmark(embedded);
  const { js, css } = mdmarkUrls();
  if (document.querySelector(`link[href="${css}"]`) === null) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = css;
    link.crossOrigin = "anonymous";
    document.head.appendChild(link);
  }
  return await importModule(js);
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

/** テストの間で読み込みの状態と mdmark の設定を消す */
export const resetLibrariesForTest = (): void => {
  loading.clear();
  loaded.clear();
  failed.clear();
  setMdmarkSettings(undefined, undefined);
  importModule = importByUrl;
};

/** テストで mdmark の `import()` を差し替える */
export const setMdmarkImportForTest = (fake: ImportModule): void => {
  importModule = fake;
};
