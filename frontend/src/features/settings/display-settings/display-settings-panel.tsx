// 表示の設定（画面設計『表示の設定.tsx』）。表示する種類と差分のミニマップと本文の表とセクションの見せ方を、この端末だけの個人の上書きとして変える左のパネル
import { useEffect, useRef, useState } from "react";

import { SettingsPanel } from "@/features/settings/display-settings/components/settings-panel";
import { SettingsConfirmDialog } from "@/features/settings/display-settings/settings-confirm-dialog";
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { displayDefaults, overrideNames, resetPrefs } from "@/shared/core/display";
import type { BodyView } from "@/shared/core/markdown-decorate";
import { KIND_KEYS, type Kind } from "@/shared/core/records";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";
import { useVisibleKinds } from "@/shared/hooks/use-visible-kinds";
import { markDisplaySaved, useDisplayMessage } from "@/shared/stores/display-notice-store";
import { readPrefs, usePrefs, writePrefs } from "@/shared/stores/prefs-store";
import { useThemeStore } from "@/shared/stores/theme-store";

/** 本文の見せ方の項目 → 端末の保存領域のキーと、上書きにする値 */
const BODY_VIEW_PREFS = { pin: "tablePin", head: "tableHead", stripes: "tableStripes", fold: "sectionFold" } as const satisfies Record<keyof BodyView, string>;

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
  const { rawIndex } = useRecords();
  const prefs = usePrefs();
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
  const look = prefs.look ?? defaults.look;
  const visibleKinds = KIND_KEYS.filter((kind) => visible.has(kind));
  const themeOverride = (readPrefs() as Record<string, unknown>)["theme"];
  const counts = Object.fromEntries(KIND_KEYS.map((kind) => [kind, rawIndex?.data[kind].length ?? 0])) as Record<Kind, number>;
  const bodyView: BodyView = { pin: prefs.tablePin !== false, head: prefs.tableHead !== false, stripes: prefs.tableStripes === true, fold: prefs.sectionFold !== false };
  const close = (): void => {
    setPanel(undefined);
  };
  return (
    <>
      <div data-scrim aria-hidden="true" className="fixed inset-0 z-20 bg-foreground/40 max-lg:hidden" onClick={close} />
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- パネルが Esc を受ける */}
      <section
        role="dialog"
        aria-modal="true"
        aria-label="表示の設定"
        className="fixed inset-y-0 left-0 z-30 flex w-96 max-w-full flex-col border-r border-border bg-card max-lg:w-full"
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
            look={look}
            defaultLook={defaults.look}
            visibleKinds={visibleKinds}
            defaultKinds={defaults.kinds}
            counts={counts}
            overrides={overrideNames({ prefs, theme: themeOverride === "light" || themeOverride === "dark" ? themeOverride : null })}
            canSave
            message={message}
            storageAvailable={storageWorks()}
            minimap={prefs.minimap !== false}
            bodyView={bodyView}
            onKindsChange={(kinds) => { writePrefs({ kinds }); }}
            onReset={() => {
              writePrefs(resetPrefs(readPrefs()));
              clearTheme();
            }}
            onSaveDefault={() => { setConfirming(true); }}
            onClose={close}
            onMinimapChange={(shown) => { writePrefs({ minimap: shown ? null : false }); }}
            onBodyViewChange={(key, value) => {
              const name = BODY_VIEW_PREFS[key];
              const isDefault = key === "stripes" ? !value : value;
              writePrefs({ [name]: isDefault ? null : value });
            }}
            onWorkspace={() => {
              // 設定の画面は本文の区画を置き換えるので、パネルを閉じて移る（履歴に積む）
              openList("settings", {});
            }}
          />
        </div>
      </section>
      <SettingsConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        from={{ look: defaults.look, visibleKinds: defaults.kinds }}
        to={{ look, visibleKinds }}
        onSaved={markDisplaySaved}
      />
    </>
  );
};
