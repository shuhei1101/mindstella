// 書き換えの知らせがつながっているか（インターフェース定義『SPAを開く』の制約「接続の状態」）
import { create } from "zustand";

export type Connection = "online" | "offline";

type ConnectionState = {
  /** トップバーの `connection` に渡す */
  connection: Connection;
  /** 更新のボタンで接続し直している間か。トップバーの `refreshing` に渡す */
  refreshing: boolean;
  /** 接続の状態を書き換える */
  setConnection: (connection: Connection) => void;
  /** 接続し直している間かを書き換える */
  setRefreshing: (refreshing: boolean) => void;
};

export const useConnectionStore = create<ConnectionState>()((set) => ({
  connection: "online",
  refreshing: false,
  setConnection: (connection) => {
    set({ connection });
  },
  setRefreshing: (refreshing) => {
    set({ refreshing });
  },
}));
