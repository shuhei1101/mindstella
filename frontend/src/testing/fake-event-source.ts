// テスト用の EventSource: テストから open・changed・duplicate_ids・error を送る
type Listener = (event: Event) => void;

export class FakeEventSource {
  static last: FakeEventSource | undefined;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  readonly url: string;
  closed = false;
  /** 接続の状態（EventSource.OPEN / CLOSED）。テストから閉じた状態にできる */
  readyState: number = FakeEventSource.OPEN;
  private readonly listeners = new Map<string, Listener[]>();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.last = this;
  }

  /** 種類ごとに受け手を足す */
  addEventListener(type: string, listener: Listener): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  /** テストから種類の知らせを送る（data を渡すと MessageEvent で送る） */
  emit(type: string, data?: string): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(data === undefined ? new Event(type) : new MessageEvent(type, { data }));
    }
  }

  /** つながりを閉じる */
  close(): void {
    this.closed = true;
    this.readyState = FakeEventSource.CLOSED;
  }
}
