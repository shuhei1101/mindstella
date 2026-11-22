// 2 回目からの GET の応答を、release を呼ぶまで止める MSW の handler（書き込みの後の再読み込みを待つかを確かめる）
import { http, HttpResponse } from "msw";

import { server } from "@/testing/msw/server";

/** `path` の GET を数え、2 回目からは `release` を呼ぶまで `body` を返さない */
export const gateRefetch = (path: string, body: unknown) => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const state = { gets: 0, release: () => { release(); } };
  server.use(
    http.get(path, async () => {
      state.gets += 1;
      if (state.gets > 1) await gate;
      return HttpResponse.json(body);
    }),
  );
  return state;
};
