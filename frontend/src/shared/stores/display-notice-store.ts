// 表示の設定の知らせ（ワークスペースの既定が変わった知らせと、表示の設定のパネルの `message`）。パネルを開いていなくても知らせ、自分が既定にした直後は知らせない
import { create } from "zustand";

import type { SettingsDisplay } from "@/shared/api/generated/model";
import { formatJst } from "@/shared/core/format";

/** 表示の設定のパネルの `message` */
export type DisplayMessage = { kind: "ok" | "info"; text: string };

type DisplayNoticeState = {
  /** 自分が既定にしようとしている値（読み直した記録で同じ値が届いたら、知らせずに外す） */
  saving: SettingsDisplay | null;
  /** パネルの `message` */
  message: DisplayMessage | null;
  /** 画面の下に出している知らせを出した日時（出していなければ null） */
  noticeAt: string | null;
};

/** 既定の値が同じか（見た目と表示する種類を、並びまで比べる） */
export const sameDisplay = (a: SettingsDisplay | null | undefined, b: SettingsDisplay | null | undefined): boolean => {
  const key = (display: SettingsDisplay | null | undefined): string => JSON.stringify([display?.network_look ?? null, display?.visible_kinds ?? null]);
  return key(a) === key(b);
};

const useDisplayNoticeStore = create<DisplayNoticeState>()(() => ({ saving: null, message: null, noticeAt: null }));

/** パネルの `message` */
export const useDisplayMessage = (): DisplayMessage | null => useDisplayNoticeStore((state) => state.message);

/** 画面の下に出している知らせの日時 */
export const useDisplayNoticeAt = (): string | null => useDisplayNoticeStore((state) => state.noticeAt);

/** 既定にする前に、保存しようとしている値を控える */
export const expectDisplaySave = (display: SettingsDisplay): void => {
  useDisplayNoticeStore.setState({ saving: display });
};

/** 既定にできなかったとき、控えた値を外す */
export const cancelDisplaySave = (): void => {
  useDisplayNoticeStore.setState({ saving: null });
};

/** 既定にできたとき、パネルに保存した旨を残す */
export const markDisplaySaved = (at: string): void => {
  useDisplayNoticeStore.setState({ message: { kind: "ok", text: `ワークスペースの既定にしました（${formatJst(at)}）。` } });
};

/** 読み直した記録の既定が前と違うとき、画面の下の知らせとパネルの `message` を出す。自分が既定にした値と同じなら知らせない */
export const displayChanged = ({ next, at }: { next: SettingsDisplay | undefined; at: string }): void => {
  const { saving } = useDisplayNoticeStore.getState();
  if (saving !== null && sameDisplay(saving, next)) {
    useDisplayNoticeStore.setState({ saving: null });
    return;
  }
  useDisplayNoticeStore.setState({ saving: null, noticeAt: at, message: { kind: "info", text: `ワークスペースの既定が変わりました（${formatJst(at)}）。` } });
};

/** 画面の下の知らせを消す */
export const clearDisplayNotice = (): void => {
  useDisplayNoticeStore.setState({ noticeAt: null });
};
