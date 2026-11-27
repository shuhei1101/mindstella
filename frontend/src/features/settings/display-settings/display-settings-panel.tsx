// 表示の設定（画面設計『表示の設定.tsx』）。表示する種類と差分のミニマップと本文の表とセクションの見せ方を、この端末だけの個人の上書きとして変える左のパネル
import { useEffect, useRef, useState } from "react";

import { SettingsPanel } from "@/features/settings/display-settings/components/settings-panel";
import { SettingsConfirmDialog } from "@/features/settings/display-settings/settings-confirm-dialog";
import { LeftPanel } from "@/shared/components/left-panel";
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { displayDefaults, overrideNames, resetPrefs } from "@/shared/core/display";
import { isEmbedded } from "@/shared/core/embedded";
import type { BodyView } from "@/shared/core/markdown-decorate";
import { KIND_KEYS, type Kind } from "@/shared/core/records";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";
import { useVisibleKinds } from "@/shared/hooks/use-visible-kinds";
import { markDisplaySaved, useDisplayMessage } from "@/shared/stores/display-notice-store";
import { readPrefs, usePointerCoarse, usePrefs, writePrefs } from "@/shared/stores/prefs-store";
import { useThemeStore } from "@/shared/stores/theme-store";

/** 本文の見せ方の項目 → 端末の保存領域のキーと、上書きにする値 */
const BODY_VIEW_PREFS = { fold: "sectionFold" } as const satisfies Record<keyof BodyView, string>;

/** 端末の保存領域に書けるか */
const storageWorks = (): boolean => {
  try {
    const key = "mindmap-preview-probe";
    localStorage.setItem(key, "1");
    localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
};

export const DisplaySettingsPanel = () => {
  const { setPanel, openList } = usePreviewSearch();
  // 配る書き出しは「ワークスペースの既定にする」と「設定を編集する」を出さない
  const embedded = isEmbedded();
  const { rawIndex } = useRecords();
  const prefs = usePrefs();
  const pointerCoarse = usePointerCoarse();
  const visible = useVisibleKinds();
  const clearTheme = useThemeStore((state) => state.clearTheme);
  const message = useDisplayMessage();
  const [confirming, setConfirming] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  // 開いたときに見出しへフォーカスを移す（パネルが Esc を受ける）
  useEffect(() => {
    heading.current?.focus();
  }, []);
  const defaults = displayDefaults(rawIndex?.data.settings.display);
  const visibleKinds = KIND_KEYS.filter((kind) => visible.has(kind));
  const themeOverride = (readPrefs() as Record<string, unknown>)["theme"];
  const counts = Object.fromEntries(KIND_KEYS.map((kind) => [kind, rawIndex?.data[kind].length ?? 0])) as Record<Kind, number>;
  const bodyView: BodyView = { fold: prefs.sectionFold !== false };
  const close = (): void => {
    setPanel(undefined);
  };
  return (
    <>
      <div data-scrim aria-hidden="true" className="fixed inset-x-0 top-below-topbar bottom-0 z-20 bg-foreground/40 max-lg:hidden" onClick={close} />
      <LeftPanel
        as="section"
        role="dialog"
        aria-modal="true"
        aria-label="表示の設定"
        className="fixed top-below-topbar bottom-0 left-0 z-30 flex w-96 max-w-full flex-col border-r border-border bg-card max-lg:w-full"
        onKeyDown={(event) => {
          if (event.key === "Escape" && !confirming) {
            event.stopPropagation();
            close();
          }
        }}
      >
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <h2 ref={heading} tabIndex={-1} className="m-0 flex-1 text-body font-medium focus-visible:outline-none">
            表示の設定
          </h2>
          <Button variant="ghost" size="icon" aria-label="表示の設定を閉じる" onClick={close}>
            <Icon name="x" />
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <SettingsPanel
            visibleKinds={visibleKinds}
            defaultKinds={defaults.kinds}
            counts={counts}
            overrides={overrideNames({ prefs, theme: themeOverride === "light" || themeOverride === "dark" ? themeOverride : null })}
            canSave={!embedded}
            message={message}
            storageAvailable={storageWorks()}
            minimap={prefs.minimap !== false}
            bodyView={bodyView}
            focusAfterAdd={prefs.focusAfterAdd ?? "auto"}
            pointerCoarse={pointerCoarse}
            // 自動は上書きを外し、入力欄へ戻す・戻さないだけを上書きとして残す
            onFocusAfterAddChange={(value) => { writePrefs({ focusAfterAdd: value === "auto" ? null : value }); }}
            singleKeyShortcuts={prefs.singleKeyShortcuts !== false}
            // 使用する（既定）は上書きを外し、使用しないだけを上書きとして残す
            onSingleKeyShortcutsChange={(value) => { writePrefs({ singleKeyShortcuts: value ? null : false }); }}
            favoritesFirst={prefs.favoritesFirst !== false}
            // 先頭に並べる（既定）は上書きを外し、並べないだけを上書きとして残す
            onFavoritesFirstChange={(value) => { writePrefs({ favoritesFirst: value ? null : false }); }}
            favoritesOnly={prefs.favoritesOnly === true}
            onFavoritesOnlyChange={(value) => { writePrefs({ favoritesOnly: value ? true : null }); }}
            onKindsChange={(kinds) => { writePrefs({ kinds }); }}
            onReset={() => {
              writePrefs(resetPrefs(readPrefs()));
              clearTheme();
            }}
            onSaveDefault={() => { setConfirming(true); }}
            onClose={close}
            onMinimapChange={(shown) => { writePrefs({ minimap: shown ? null : false }); }}
            onBodyViewChange={(key, value) => {
              writePrefs({ [BODY_VIEW_PREFS[key]]: value ? null : value });
            }}
            onWorkspace={embedded ? undefined : () => {
              // 設定の画面は本文の区画を置き換えるので、パネルを閉じて移る（履歴に積む）
              openList("settings", {});
            }}
          />
        </div>
      </LeftPanel>
      <SettingsConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        from={{ visibleKinds: defaults.kinds }}
        to={{ visibleKinds }}
        onSaved={markDisplaySaved}
      />
    </>
  );
};
