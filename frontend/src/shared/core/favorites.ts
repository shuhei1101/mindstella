// お気に入りの計算（DOM と保存領域に触らない）
/** 星の列のキー */
export const FAVORITE_COLUMN_KEY = "favorite";

/** 星の列の並べ替えの値（昇順でお気に入りが先頭になる順） */
export const FAVORITE_ORDER = ["★", ""] as const;

/** お気に入りを先頭に寄せる。お気に入りの中とそれ以外の中は渡した順のまま */
export const favoritesFirst = <T extends { id: string }>(items: readonly T[], favorites: ReadonlySet<string>): T[] => [
  ...items.filter((item) => favorites.has(item.id)),
  ...items.filter((item) => !favorites.has(item.id)),
];

/** お気に入りの項目だけに絞る */
export const favoritesOnly = <T extends { id: string }>(items: readonly T[], favorites: ReadonlySet<string>): T[] => items.filter((item) => favorites.has(item.id));

/** 登録していなければ末尾に加え、登録していれば外す */
export const toggleFavorite = (favorites: readonly string[], id: string): string[] => (favorites.includes(id) ? favorites.filter((one) => one !== id) : [...favorites, id]);
