// テスト用の EventSource: テストから open・changed・error を送る
type Listener = (event: Event) => void;

export class FakeEventSource {
  static last: FakeEventSource | undefined;
  readonly url: string;
  closed = false;
  private readonly listeners = new Map<string, Listener[]>();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.last = this;
  }

  /** 種類ごとに受け手を足す */
  addEventListener(type: string, listener: Listener): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  /** テストから種類の知らせを送る */
  emit(type: string): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(new Event(type));
    }
  }

  /** つながりを閉じる */
  close(): void {
    this.closed = true;
  }
}
