// 図の種類ごとの前後と、色を付けるべき要素の文字（期待値）
window.CASES = [
  {
    name: "flowchart",
    before: "flowchart TD\n  A[開始] -->|受け付ける| B[処理]\n  B -->|確かめる| C[確認]\n  C -->|終える| D[終了]",
    after: "flowchart TD\n  A[開始] -->|受け付ける| B[処理する]\n  B -->|確かめる| C[確認]\n  C -->|知らせる| E[通知]\n  A -->|飛ばす| C",
    expected: { added: ["通知", "知らせる", "飛ばす"], changed: ["処理する"], removedNodes: ["終了"] },
  },
  {
    name: "sequenceDiagram",
    before: "sequenceDiagram\n  participant U as 利用者\n  participant S as サーバー\n  participant D as 保存先\n  U->>S: 送る\n  S->>D: 書く\n  S-->>U: 返す",
    after: "sequenceDiagram\n  participant U as 利用者\n  participant S as 配信サーバー\n  participant N as 通知\n  U->>S: 送る\n  S->>N: 知らせる\n  S-->>U: 返す",
    expected: { added: ["通知", "知らせる"], changed: ["配信サーバー"], removedNodes: ["保存先"] },
  },
  {
    name: "classDiagram",
    before: "classDiagram\n  class Store\n  class Item\n  class Log\n  Store --> Item : 持つ\n  Store --> Log : 書く",
    after: "classDiagram\n  class Store\n  class Item {\n    +title\n  }\n  class Tag\n  Store --> Item : 持つ\n  Item --> Tag : 付ける",
    expected: { added: ["Tag", "付ける"], changed: ["Item+title"], removedNodes: ["Log"] },
  },
  {
    name: "erDiagram",
    before: "erDiagram\n  USER ||--o{ ORDER : places\n  ORDER ||--|{ LINE : contains\n  USER {\n    string id\n  }",
    after: "erDiagram\n  USER ||--o{ ORDER : places\n  ORDER }o--|| PRODUCT : refers\n  USER {\n    string id\n    string name\n  }",
    expected: { added: ["PRODUCT", "refers"], changed: ["USERstringidstringname"], removedNodes: ["LINE"] },
  },
  {
    name: "stateDiagram-v2",
    before: "stateDiagram-v2\n  [*] --> 未着手 : 作る\n  未着手 --> 進行中 : 着手\n  進行中 --> 保留 : 止める\n  進行中 --> [*] : 終える",
    after: "stateDiagram-v2\n  [*] --> 未着手 : 作る\n  未着手 --> 進行中 : 着手\n  進行中 : 作業している\n  未着手 --> 中止 : やめる\n  進行中 --> [*] : 終える",
    expected: { added: ["中止", "やめる"], changed: ["作業している"], removedNodes: ["保留"] },
  },
];
