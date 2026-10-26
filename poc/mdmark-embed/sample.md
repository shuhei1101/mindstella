# 返信の速さの検討

返信の速さは応答時間で測る。応答時間が短いほど良い。自分の別名・古い語・古い調査の語には印を付けない。

<!-- html -->

```html
<div style="display: flex; gap: 12px">
  <div style="padding: 12px; border: 1px solid currentColor" data-hint="受け取りの段">受け取り: 応答時間を記録する（A-2）</div>
  <div style="padding: 12px; border: 1px solid currentColor">分類</div>
</div>
<mdmark-chart>
{
  "type": "line",
  "title": "曜日ごとの返信",
  "scope": "10 月の第 2 週",
  "updated": "2026-10-17",
  "x": { "label": "曜日", "ticks": ["月", "火", "水", "木", "金"] },
  "y": { "label": "秒" },
  "series": [{ "name": "平均", "points": [12, 9, 14, 8, 11] }]
}
</mdmark-chart>
<mdmark-param>
{
  "title": "返信の速さの見積もり",
  "knob": { "key": "strength", "label": "反応の強さ", "min": 0, "max": 2, "step": 1, "value": 1 },
  "chart": {
    "title": "反応の強さごとの返信の進み",
    "scope": "経過 0〜4 秒",
    "updated": "2026-10-18",
    "x": { "label": "経過（秒）", "ticks": ["0", "2", "4"] },
    "y": { "label": "返信の進み（%）", "min": 0, "max": 100, "step": 25 }
  },
  "table": { "0": [0, 0, 0], "1": [0, 40, 70], "2": [0, 60, 90] }
}
</mdmark-param>
```

<!-- /html -->

詳しくは A-2 と ＲＥＳＰＯＮＳＥ を見る。応答時間 の目安は 10 秒。 LATENCY も見る。

```html
<p>範囲の外の html のコードブロック</p>
```
