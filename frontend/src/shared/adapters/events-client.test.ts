import { QueryClient } from "@tanstack/react-query";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { connectEvents } from "@/shared/adapters/events-client";
import { useConnectionStore } from "@/shared/stores/connection-store";
import { FakeEventSource } from "@/testing/fake-event-source";

describe("connectEvents", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", FakeEventSource);
    useConnectionStore.setState({ connection: "online" });
  });

  // changed で読み直す（正常系）
  test("connect_events_when_changed", () => {
    // 準備
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    connectEvents(queryClient);
    // 実行
    FakeEventSource.last?.emit("changed");
    // 検証
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["/api/records"] });
  });

  // 切れたら offline（正常系）
  test("connect_events_when_error", () => {
    // 準備
    connectEvents(new QueryClient());
    // 実行
    FakeEventSource.last?.emit("error");
    const afterError = useConnectionStore.getState().connection;
    FakeEventSource.last?.emit("open");
    // 検証
    expect(afterError).toBe("offline");
    expect(useConnectionStore.getState().connection).toBe("online");
  });
});
