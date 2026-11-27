// 資料の画面のストーリー。お気に入りの星・先頭への並び・お気に入りだけの表示と、データの量の場面を並べる
import type { Meta, StoryObj } from "@storybook/react-vite";
import { http, HttpResponse } from "msw";
import { expect, userEvent, within } from "storybook/test";

import { DocsScreen } from "@/features/docs/docs/docs-screen";
import { worker } from "@/testing/msw/browser";
import { RECORDS } from "@/testing/msw/handlers";
import { InStoryRouter } from "@/testing/story-router";
import { PREFS_KEY } from "@/shared/stores/theme-store";

const Screen = () => <DocsScreen drawerOpen={false} onCloseDrawer={() => undefined} />;

/** 作成日時を i 日ずつずらした資料 */
const doc = (n: number, title: string, status = "確認中") => {
  const day = String((n % 28) + 1).padStart(2, "0");
  return { id: `A-${String(n)}`, title, status, kind: "比較", tags: [{ name: "画面" }], created: `2026-11-${day}T00:00:00+00:00`, updated: `2026-11-${day}T00:00:00+00:00`, body: "## 比較\n\n本文" };
};

const DOCS = [doc(1, "画面の配色の比較"), doc(2, "一覧の並べ替えの調査"), doc(3, "お気に入りの置き場所の比較", "完成")];

const LONG_DOCS = [
  doc(1, "カードの一覧とボードと表のそれぞれで、お気に入りに登録した資料をどの位置に並べるかと、表示の設定で切り替えたときの見え方を比べた長いタイトルの資料"),
  doc(2, "長い英字を含む資料 FavoriteToggleAriaPressedStateAndKeyboardOperationNotes"),
  doc(3, "短い資料"),
];

const MANY_DOCS = Array.from({ length: 40 }, (_, index) => doc(index + 1, `資料 ${String(index + 1)} の比較`, index % 3 === 0 ? "完成" : "確認中"));

/** 記録の資料と、端末の保存領域の表示の上書きを用意する */
const prepare = (docs: unknown[], prefs: Record<string, unknown>) => () => {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  worker.use(http.get("*/api/records", () => HttpResponse.json({ ...RECORDS, docs })));
  return () => {
    localStorage.removeItem(PREFS_KEY);
  };
};

const meta = {
  title: "Features/Docs/DocsScreen",
  component: InStoryRouter,
  parameters: { layout: "fullscreen" },
  beforeEach: prepare(DOCS, { favorites: ["A-1"] }),
  args: { path: "/?tab=docs&sort=id", screen: Screen },
} satisfies Meta<typeof InStoryRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** カードの一覧。お気に入りの A-1 の右上に塗った星を出し、先頭に並べる。ほかのカードの星は線だけ */
export const FavoritesFirst: Story = {};

/** 「お気に入りを一番上にする」をオフにした。カードは並べ替えの順のまま、星だけを出す */
export const FavoritesFirstOff: Story = { beforeEach: prepare(DOCS, { favorites: ["A-1"], favoritesFirst: false }) };

/** カードの星を押して A-3 を登録した。A-3 の星を塗り、お気に入りの中の順で先頭に並ぶ。詳細パネルは開かない */
export const ToggleOnCard: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const star = await canvas.findByRole("button", { name: "お気に入りの置き場所の比較をお気に入りに登録" });
    await userEvent.click(star);
    await expect(await canvas.findByRole("button", { name: "お気に入りの置き場所の比較をお気に入りに登録", pressed: true })).toBeInTheDocument();
  },
};

/** ボード。星を出すだけで、列の中の並びは変えない */
export const Board: Story = { args: { path: "/?tab=docs&view=board&sort=id" } };

/** 表。一番左の星の列でお気に入りの行の星を塗る */
export const Table: Story = { args: { path: "/?tab=docs&view=table" } };

/** 表を星の列で昇順に並べた。お気に入りが先頭で、見出しの `aria-sort` は ascending */
export const TableSortedByFavorite: Story = { args: { path: "/?tab=docs&view=table&sort=favorite" } };

/** 「お気に入りだけを表示する」をオンにした。カードは A-1 だけ */
export const FavoritesOnly: Story = { beforeEach: prepare(DOCS, { favorites: ["A-1"], favoritesOnly: true }) };

/** 「お気に入りだけを表示する」をオンにして、お気に入りが 1 件も無い。該当なしの文言を出す */
export const FavoritesOnlyNone: Story = { beforeEach: prepare(DOCS, { favorites: [], favoritesOnly: true }) };

/** 記録に無い A-9 が端末の保存領域のお気に入りに残っている。A-9 のカードは出さず、A-1 だけを先頭に並べる */
export const MissingFavorite: Story = { beforeEach: prepare(DOCS, { favorites: ["A-9", "A-1"] }) };

/** 長いタイトル。星はカードの右上に留まり、タイトルは星と重ならずに折り返す */
export const LongText: Story = { beforeEach: prepare(LONG_DOCS, { favorites: ["A-1", "A-2"] }) };

/** 資料 40 件のうち 3 件がお気に入り。お気に入りが先頭の 3 枚に並ぶ */
export const Many: Story = { beforeEach: prepare(MANY_DOCS, { favorites: ["A-7", "A-20", "A-33"] }) };

/** 資料が 0 件 */
export const Empty: Story = { beforeEach: prepare([], { favorites: ["A-1"] }) };
