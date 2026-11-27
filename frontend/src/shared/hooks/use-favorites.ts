// お気に入りと、その並び・絞り込みの上書きを端末の保存領域から読み、登録・解除する
import { readPrefs, usePrefs, writePrefs } from "@/shared/stores/prefs-store";
import { toggleFavorite } from "@/shared/core/favorites";

export type Favorites = {
  /** お気に入りに登録した項目の ID */
  ids: ReadonlySet<string>;
  /** カードの一覧でお気に入りを先頭に並べるか */
  first: boolean;
  /** お気に入りの項目だけを表示するか */
  only: boolean;
  /** 項目をお気に入りに登録・解除する */
  toggle: (id: string) => void;
  /** 「お気に入りだけを表示する」の上書きを外す */
  clearOnly: () => void;
};

export const useFavorites = (): Favorites => {
  const prefs = usePrefs();
  return {
    ids: new Set(prefs.favorites ?? []),
    first: prefs.favoritesFirst !== false,
    only: prefs.favoritesOnly === true,
    toggle: (id) => {
      writePrefs({ favorites: toggleFavorite(readPrefs().favorites ?? [], id) });
    },
    clearOnly: () => {
      writePrefs({ favoritesOnly: null });
    },
  };
};
