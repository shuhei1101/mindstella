// 書き換えの知らせがつながっているか（インターフェース定義『SPAを開く』の制約「接続の状態」）
import { create } from "zustand";

export type Connection = "online" | "offline";

type ConnectionState = {
  /** トップバーの `connection` に渡す */
  connection: Connection;
  /** 接続の状態を書き換える */
  setConnection: (connection: Connection) => void;
};

export const useConnectionStore = create<ConnectionState>()((set) => ({
  connection: "online",
  setConnection: (connection) => {
    set({ connection });
  },
}));
