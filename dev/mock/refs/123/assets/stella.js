// ネットワークの 5 つの見た目。app.js が毎コマ計算した玉・線を受け取り、見た目ごとの描き方で描く
// starlight・deep の線は両端の色の中間の単色で 1 本ずつ引き、光の玉と光条は色ごとに一度だけ絵に焼いて置く
(() => {
  const TAU = Math.PI * 2;
  const FOCAL = 700;            // app.js の透視投影と同じ焦点距離
  const FLOW_PERIOD = 4200;     // 線の上を玉が流れる 1 周の時間（ms）
  const TWINKLE_PERIOD = 1900;  // 星のまたたきの周期（ms）
  const PULSE_PERIOD = 3600;    // 選んだ星から広がる輪の周期（ms）
  const SPRITE = 128;           // 光の玉の絵の一辺（px）

  /** 文字列から 0〜1 の決まった値を作る（玉ごとのまたたきの位相に使う） */
  const hash = (s) => { let h = 2166136261; for (const c of s) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return ((h >>> 0) % 10000) / 10000; };
  /** 種を決めた乱数を返す（空の星の配置を毎回同じにする） */
  const seeded = (a) => () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  /** #rrggbb を [r, g, b] にする */
  const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  /** #rrggbb に透明度を付けた色を返す */
  const rgba = (hex, a) => { const [r, g, b] = rgb(hex); return `rgba(${r},${g},${b},${a})`; };
  /** 色を白へ寄せる（星の芯の色に使う） */
  const whiten = (hex, k) => "#" + rgb(hex).map((v) => Math.round(v + (255 - v) * k).toString(16).padStart(2, "0")).join("");

  const sprites = new Map();
  /** 中心が明るく外へ薄れる光の玉の絵を、色と減衰ごとに一度だけ作って返す */
  const glow = (hex, falloff) => {
    const key = hex + falloff;
    if (sprites.has(key)) return sprites.get(key);
    const c = document.createElement("canvas"); c.width = c.height = SPRITE;
    const x = c.getContext("2d"), h = SPRITE / 2, g = x.createRadialGradient(h, h, 0, h, h, h), [r, gg, b] = rgb(hex);
    // 減衰の曲線を 12 段で近似する
    for (let i = 0; i <= 12; i++) { const t = i / 12; g.addColorStop(t, `rgba(${r},${gg},${b},${Math.pow(1 - t, falloff)})`); }
    x.fillStyle = g; x.fillRect(0, 0, SPRITE, SPRITE);
    sprites.set(key, c);
    return c;
  };
  /** 光の玉の絵を、中心と半径を指定して置く */
  const blit = (ctx, img, x, y, r) => ctx.drawImage(img, x - r, y - r, r * 2, r * 2);
  /** 2 点を結ぶ線を引く。dash は線の種類の見分け（実線・点線・破線・一点鎖線） */
  const line = (ctx, a, b, dash = []) => { ctx.setLineDash(dash); ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy); ctx.stroke(); };
  /** 線の種類の破線の並び */
  const dashOf = (e, l) => e.dash[l.type] || [];
  /** 塗りの円を描く */
  const circle = (ctx, x, y, r) => { ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); };
  /** 4 方向へとがった星の形（アストロイド）を塗る */
  const star4 = (ctx, x, y, r) => {
    ctx.beginPath(); ctx.moveTo(x, y - r);
    ctx.quadraticCurveTo(x, y, x + r, y); ctx.quadraticCurveTo(x, y, x, y + r);
    ctx.quadraticCurveTo(x, y, x - r, y); ctx.quadraticCurveTo(x, y, x, y - r);
    ctx.fill();
  };
  const RAY_W = 3;              // 光条の絵の筋の太さ（px）
  const rays = new Map();
  /** 十字の光の筋の絵を、色ごとに一度だけ作って返す（毎コマはグラデーションを作らず置くだけにする） */
  const ray = (hex) => {
    if (rays.has(hex)) return rays.get(hex);
    const c = document.createElement("canvas"); c.width = c.height = SPRITE;
    const x = c.getContext("2d"), h = SPRITE / 2;
    for (const [dx, dy] of [[1, 0], [0, 1]]) {
      const g = x.createLinearGradient(h - dx * h, h - dy * h, h + dx * h, h + dy * h);
      g.addColorStop(0, rgba(hex, 0)); g.addColorStop(0.5, rgba(hex, 1)); g.addColorStop(1, rgba(hex, 0));
      x.fillStyle = g;
      x.fillRect(dx ? 0 : h - RAY_W / 2, dy ? 0 : h - RAY_W / 2, dx ? SPRITE : RAY_W, dy ? SPRITE : RAY_W);
    }
    rays.set(hex, c);
    return c;
  };
  /** 明るい星の光条（十字の光の筋）を、焼いた絵を長さに合わせて置いて描く */
  const spikes = (ctx, x, y, len, hex, alpha) => { ctx.globalAlpha = alpha; blit(ctx, ray(hex), x, y, len); };
  /** 注目している線の上を流れる玉の位置（0〜1）を、1 本に 2 つずつ返す */
  const flows = (e, s) => [0, 0.5].map((off) => ((e.now / FLOW_PERIOD) + off + (s.l.a.length % 7) * 0.13) % 1);
  /** 線の位置 t の画面座標を返す */
  const at = (s, t) => ({ x: s.from.sx + (s.to.sx - s.from.sx) * t, y: s.from.sy + (s.to.sy - s.from.sy) * t });
  /** 選んだ玉・カーソルを乗せた玉に輪を付ける */
  const ring = (e, d, gap = 4) => {
    if (!d.selected && !d.hover) return;
    const { ctx } = e;
    ctx.setLineDash([]); ctx.globalAlpha = 0.9; ctx.strokeStyle = e.C.ring; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(d.p.sx, d.p.sy, d.rad + gap, 0, TAU); ctx.stroke();
  };
  /** 玉の基本の濃さ（奥ほど薄く、沈めた玉・手前すぎる玉は薄く） */
  const alphaOf = (d) => (0.35 + 0.55 * d.depth) * d.dim * d.close;
  /** 星のまたたき（ゆっくり明るさが揺れる） */
  const twinkle = (e, d, amp) => 1 - amp + amp * Math.sin(e.now / TWINKLE_PERIOD + d.seed * TAU);
  /** 選んだ玉から、ゆっくり広がって消える輪を描く */
  const pulse = (e, d, hex) => {
    const ph = (e.now % PULSE_PERIOD) / PULSE_PERIOD, { ctx } = e;
    ctx.setLineDash([]); ctx.globalAlpha = Math.pow(1 - ph, 2) * 0.55; ctx.strokeStyle = hex; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(d.p.sx, d.p.sy, d.rad * (1.4 + ph * 5), 0, TAU); ctx.stroke();
  };
  /** 2 色の中間の色を返す */
  const mix = (ca, cb) => { const a = rgb(ca), b = rgb(cb); return "#" + a.map((v, i) => Math.round((v + b[i]) / 2).toString(16).padStart(2, "0")).join(""); };
  /** 両端の星の色の中間の単色で線を 1 本引く（線ごとのグラデーションは作らない） */
  const midLine = (ctx, a, b, ca, cb, alpha, dash) => { ctx.strokeStyle = rgba(mix(ca, cb), alpha); line(ctx, a, b, dash); };
  /** 群れのおおよその半径（近い順に 9 割目の玉まで）。星図の球の大きさに使う */
  const spread = (G) => G.R ??= (() => { const r = G.nodes.map((n) => Math.hypot(n.x, n.y, n.z)).sort((a, b) => a - b); return Math.max(40, r[Math.floor(r.length * 0.9)] || 40); })();

  // ===== 深宇宙の空: 遠い星・天の川・星雲を一度だけ作る =====
  let SKY = null;
  /** 球面の一様な向きを返す */
  const dir = (rnd) => { const u = rnd() * 2 - 1, th = rnd() * TAU, s = Math.sqrt(1 - u * u); return { x: s * Math.cos(th), y: u, z: s * Math.sin(th) }; };
  /** 深宇宙の空の素材（星の向き・明るさ・色、天の川の帯、星雲の絵）を作って返す */
  const sky = () => SKY ??= (() => {
    const rnd = seeded(20261002), tints = ["#ffffff", "#cfe0ff", "#fff1d6", "#ffd9c2", "#d9f2ff"];
    const stars = [];
    // 遠い星: 空全体に散らし、暗い星ほど多くする
    for (let i = 0; i < 900; i++) stars.push({ ...dir(rnd), m: Math.pow(rnd(), 3), c: tints[Math.floor(rnd() * tints.length)], s: rnd() });
    // 天の川: 傾けた大円のまわりに、緯度方向へ正規分布で寄せて置く
    const tilt = 0.5;
    for (let i = 0; i < 1600; i++) {
      const a = rnd() * TAU, lat = (rnd() + rnd() + rnd() - 1.5) * 0.16;
      const x = Math.cos(a) * Math.cos(lat), y0 = Math.sin(lat), z0 = Math.sin(a) * Math.cos(lat);
      stars.push({ x, y: y0 * Math.cos(tilt) - z0 * Math.sin(tilt), z: y0 * Math.sin(tilt) + z0 * Math.cos(tilt), m: Math.pow(rnd(), 2.5) * 0.8, c: tints[Math.floor(rnd() * 3)], s: rnd(), band: true });
    }
    // 星雲: 色のにじみを重ねた絵を 3 枚作り、空の 3 方向に貼る
    const palettes = [["#2dd4bf", "#6366f1", "#0ea5e9"], ["#a855f7", "#ec4899", "#6366f1"], ["#14b8a6", "#22d3ee", "#8b5cf6"], ["#6366f1", "#0ea5e9", "#a855f7"]];
    // 正四面体の 4 方向に貼り、どちらを向いても 1 枚は見えるようにする
    const k3 = 1 / Math.sqrt(3), anchors = [{ x: k3, y: k3, z: k3 }, { x: -k3, y: -k3, z: k3 }, { x: -k3, y: k3, z: -k3 }, { x: k3, y: -k3, z: -k3 }];
    const nebulae = palettes.map((pal, k) => {
      const c = document.createElement("canvas"); c.width = c.height = 512;
      const x = c.getContext("2d"); x.globalCompositeOperation = "lighter";
      // 大小のにじみを 14 個重ねて雲の形にする
      for (let i = 0; i < 14; i++) {
        const cx = 256 + (rnd() - 0.5) * 260, cy = 256 + (rnd() - 0.5) * 200, r = 60 + rnd() * 170, col = pal[i % pal.length];
        const g = x.createRadialGradient(cx, cy, 0, cx, cy, r);
        g.addColorStop(0, rgba(col, 0.22 + rnd() * 0.14)); g.addColorStop(1, rgba(col, 0));
        x.fillStyle = g; x.fillRect(0, 0, 512, 512);
      }
      return { img: c, d: anchors[k], scale: 1.5 + k * 0.2 };
    });
    return { stars, nebulae };
  })();
  /** 無限に遠い向きを画面へ写す（回転だけ。手前側に無ければ null） */
  const projDir = (e, v) => { const q = e.rot(v.x, v.y, v.z); return q.z <= 0.02 ? null : { sx: e.W / 2 + (q.x / q.z) * FOCAL, sy: e.H / 2 + (q.y / q.z) * FOCAL, z: q.z }; };

  // ===== 見た目の案 =====
  const styles = {
    glow: {
      label: "グロウ", note: "今の形のまま、玉と流れる光にやわらかい光のにじみを足す",
      /** 玉の周りに光のにじみを足す。夜は光を足し合わせて明るく重ねる */
      draw(e) {
        const { ctx, C, dark } = e;
        ctx.lineWidth = 0.6; ctx.strokeStyle = C.line;
        for (const k of e.links) { ctx.globalAlpha = (dark ? 0.3 : 0.22) * k.dep * k.fade; line(ctx, k.a, k.b, dashOf(e, k.l)); }
        for (const s of e.selLinks) {
          ctx.globalAlpha = 1; ctx.strokeStyle = C.line; ctx.lineWidth = 1; line(ctx, s.from, s.to, dashOf(e, s.l));
          if (dark) ctx.globalCompositeOperation = "lighter";
          for (const t of flows(e, s)) { const p = at(s, t); ctx.globalAlpha = Math.sin(Math.PI * t); blit(ctx, glow(C.dot, 1.8), p.x, p.y, 7); }
          ctx.globalCompositeOperation = "source-over";
        }
        for (const d of e.nodes) {
          const a = alphaOf(d);
          if (dark) ctx.globalCompositeOperation = "lighter";
          ctx.globalAlpha = a * (dark ? 0.4 : 0.22); blit(ctx, glow(d.color, 2), d.p.sx, d.p.sy, d.rad * 3.4);
          ctx.globalCompositeOperation = "source-over";
          ctx.globalAlpha = a; ctx.fillStyle = d.color; circle(ctx, d.p.sx, d.p.sy, d.rad);
          if (dark) { ctx.globalAlpha = a * 0.55; ctx.fillStyle = "#ffffff"; circle(ctx, d.p.sx, d.p.sy, d.rad * 0.35); }
          ring(e, d);
        }
      },
    },

    starlight: {
      label: "星の光", note: "白い芯と色の光、明るい星には十字の光条。ゆっくりまたたく。昼は星形の印",
      /** 玉を星として描く: 夜は白い芯と色のにじみと光条、昼は 4 方向にとがった星形 */
      draw(e) {
        const { ctx, C, dark } = e;
        ctx.lineWidth = 0.7;
        if (dark) ctx.globalCompositeOperation = "lighter";
        for (const k of e.links) { if (dark) midLine(ctx, k.a, k.b, k.ca, k.cb, 0.2 * k.dep * k.fade, dashOf(e, k.l)); else { ctx.strokeStyle = C.line; ctx.globalAlpha = 0.22 * k.dep * k.fade; line(ctx, k.a, k.b, dashOf(e, k.l)); } }
        ctx.globalAlpha = 1;
        for (const s of e.selLinks) {
          ctx.lineWidth = 1.1;
          if (dark) midLine(ctx, s.from, s.to, s.cf, s.ct, 0.75, dashOf(e, s.l)); else { ctx.strokeStyle = C.line; line(ctx, s.from, s.to, dashOf(e, s.l)); }
          for (const t of flows(e, s)) {
            const p = at(s, t), a = Math.sin(Math.PI * t);
            ctx.globalAlpha = a; blit(ctx, glow(dark ? "#ffffff" : C.dot, 2), p.x, p.y, dark ? 6 : 4);
          }
        }
        for (const d of e.nodes) {
          const a = alphaOf(d), tw = twinkle(e, d, 0.18), { sx, sy } = d.p, big = d.n.deg >= 4 || d.strong;
          if (dark) {
            ctx.globalAlpha = a * 0.28 * tw; blit(ctx, glow(d.color, 2.2), sx, sy, d.rad * 4.6);
            ctx.globalAlpha = a * 0.95; blit(ctx, glow(whiten(d.color, 0.25), 1.3), sx, sy, d.rad * 1.8);
            if (big) spikes(ctx, sx, sy, d.rad * (2.4 + Math.min(6, d.n.deg) * 0.45) * tw, whiten(d.color, 0.5), a * 0.55);
            ctx.globalAlpha = a * tw; ctx.fillStyle = "#ffffff"; circle(ctx, sx, sy, d.rad * 0.42);
          } else {
            ctx.globalAlpha = a * 0.22; blit(ctx, glow(d.color, 2), sx, sy, d.rad * 2.8);
            ctx.globalAlpha = a; ctx.fillStyle = d.color; star4(ctx, sx, sy, d.rad * (big ? 1.9 : 1.5));
          }
          ring(e, d, dark ? 5 : 6);
        }
        ctx.globalCompositeOperation = "source-over";
      },
    },

    constellation: {
      label: "星図", note: "天球の経緯線が回転に合わせて回る星図。線は星の手前で切り、選ぶと照準の輪",
      labelLift: 1.1,
      /** 星図の見た目: 天球の網・星に触れない線・照準の輪 */
      draw(e) {
        const { ctx, C, dark, G } = e, Rs = spread(G) * 2.1, grid = dark ? "170,195,255" : "35,55,105";
        // 天球の網: 経線 12 本と緯線 5 本を、奥ほど薄く描く
        ctx.lineWidth = 0.6;
        /** 球面上の点の列を、奥行きで濃さを変えながらつなぐ */
        const path = (pts, base) => {
          for (let i = 1; i < pts.length; i++) {
            const a = e.proj(pts[i - 1]), b = e.proj(pts[i]);
            if (a.z + G.dist <= 10 || b.z + G.dist <= 10) continue;
            const far = Math.max(0.15, Math.min(1, 1.3 - ((a.z + b.z) / 2 + G.dist) / (G.dist * 2)));
            ctx.strokeStyle = `rgba(${grid},${base * far})`; line(ctx, a, b);
          }
        };
        const STEP = 48;
        for (let m = 0; m < 12; m++) {
          const ph = (m / 12) * Math.PI, pts = [];
          for (let i = 0; i <= STEP; i++) { const th = (i / STEP) * TAU; pts.push({ x: Rs * Math.cos(th) * Math.cos(ph), y: Rs * Math.sin(th), z: Rs * Math.cos(th) * Math.sin(ph) }); }
          path(pts, dark ? 0.09 : 0.08);
        }
        for (const lat of [-60, -30, 0, 30, 60]) {
          const la = (lat * Math.PI) / 180, pts = [];
          for (let i = 0; i <= STEP; i++) { const ph = (i / STEP) * TAU; pts.push({ x: Rs * Math.cos(la) * Math.cos(ph), y: Rs * Math.sin(la), z: Rs * Math.cos(la) * Math.sin(ph) }); }
          path(pts, lat === 0 ? (dark ? 0.2 : 0.16) : (dark ? 0.09 : 0.08));
        }
        // 線: 星に触れないよう両端を少し手前で切る
        const ink = dark ? "#c8d4ff" : "#26365e";
        /** 星の半径ぶん両端を詰めた線を引く */
        const gapLine = (a, b, ra, rb, dash) => {
          const dx = b.sx - a.sx, dy = b.sy - a.sy, L = Math.hypot(dx, dy);
          if (L < ra + rb + 4) return;
          const ux = dx / L, uy = dy / L;
          ctx.setLineDash(dash); ctx.beginPath(); ctx.moveTo(a.sx + ux * (ra + 3), a.sy + uy * (ra + 3)); ctx.lineTo(b.sx - ux * (rb + 3), b.sy - uy * (rb + 3)); ctx.stroke();
        };
        const rOf = (n, p) => n.r * 1.05 * (p.f / e.k0) * e.ease * 0.55;
        ctx.strokeStyle = ink; ctx.lineWidth = 0.6;
        for (const k of e.links) { ctx.globalAlpha = (dark ? 0.32 : 0.3) * k.dep * k.fade; gapLine(k.a, k.b, rOf(k.l.s, k.a), rOf(k.l.t, k.b), dashOf(e, k.l)); }
        for (const s of e.selLinks) {
          ctx.globalAlpha = 0.9; ctx.lineWidth = 1.1; ctx.strokeStyle = C.ring;
          gapLine(s.from, s.to, rOf(G.nodes[G.idx.get(e.sel)], s.from) + 6, rOf(s.other, s.to), dashOf(e, s.l));
          ctx.setLineDash([]);
          for (const t of flows(e, s)) { const p = at(s, t); ctx.globalAlpha = 0.9 * Math.sin(Math.PI * t); ctx.fillStyle = C.ring; circle(ctx, p.x, p.y, 1.4); }
        }
        // 星: 小さく締まった点と、種類の色の細い輪
        ctx.setLineDash([]);
        if (dark) ctx.globalCompositeOperation = "lighter";
        for (const d of e.nodes) {
          const a = alphaOf(d), r = d.rad * 0.55, { sx, sy } = d.p;
          if (dark) { ctx.globalAlpha = a * 0.5; blit(ctx, glow(d.color, 3), sx, sy, d.rad * 2.4); }
          ctx.globalAlpha = a; ctx.fillStyle = dark ? whiten(d.color, 0.7) : ink; circle(ctx, sx, sy, r);
          ctx.globalAlpha = a * 0.7; ctx.strokeStyle = d.color; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(sx, sy, r + 2.5, 0, TAU); ctx.stroke();
        }
        ctx.globalCompositeOperation = "source-over";
        // 選んだ星の照準: ゆっくり回る 4 本の目盛りと、点線の外輪
        for (const d of e.nodes) {
          if (!d.selected && !d.hover) continue;
          const r = d.rad * 0.55 + 8, rot = e.now / 9000, { sx, sy } = d.p;
          ctx.globalAlpha = 0.95; ctx.strokeStyle = C.ring; ctx.lineWidth = 1.2;
          ctx.beginPath(); ctx.arc(sx, sy, r, 0, TAU); ctx.stroke();
          for (let i = 0; i < 4; i++) { const an = rot + (i * TAU) / 4; ctx.beginPath(); ctx.moveTo(sx + Math.cos(an) * (r + 2), sy + Math.sin(an) * (r + 2)); ctx.lineTo(sx + Math.cos(an) * (r + 7), sy + Math.sin(an) * (r + 7)); ctx.stroke(); }
          if (d.selected) { ctx.setLineDash([2, 4]); ctx.globalAlpha = 0.6; ctx.beginPath(); ctx.arc(sx, sy, r + 13, 0, TAU); ctx.stroke(); ctx.setLineDash([]); }
        }
      },
    },

    deep: {
      label: "深宇宙", note: "回転に合わせて動く星空・天の川・星雲の地に、光のにじむ星。選ぶと彗星が線を流れ、輪が広がる。昼は夜明けの空",
      /** いちばん豪華な案: 星空の地・光を重ねた星・彗星の流れ・広がる輪 */
      draw(e) {
        const { ctx, C, dark, W, H, G } = e, S = sky();
        // 地: 夜は深い紺から黒へ、昼は淡い青から生成りへ
        const bg = dark ? ctx.createRadialGradient(W / 2, H * 0.45, 0, W / 2, H / 2, Math.max(W, H) * 0.75) : ctx.createLinearGradient(0, 0, 0, H);
        if (dark) { bg.addColorStop(0, "#0d1428"); bg.addColorStop(0.6, "#070a16"); bg.addColorStop(1, "#030409"); }
        else { bg.addColorStop(0, "#e8edf8"); bg.addColorStop(0.55, "#f3f1f6"); bg.addColorStop(1, "#f8f4ec"); }
        ctx.globalAlpha = 1; ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
        // 星雲: 空の向きに貼ってあり、回すと一緒に流れる
        ctx.globalCompositeOperation = dark ? "lighter" : "source-over";
        for (const nb of S.nebulae) {
          const p = projDir(e, nb.d);
          if (!p) continue;
          const size = Math.max(W, H) * nb.scale;
          ctx.globalAlpha = (dark ? 0.75 : 0.35) * Math.min(1, p.z * 2.5);
          ctx.drawImage(nb.img, p.sx - size / 2, p.sy - size / 2, size, size);
        }
        // 遠い星と天の川（夜だけ）。ゆっくりまたたく
        if (dark) for (const st of S.stars) {
          const p = projDir(e, st);
          if (!p || p.sx < -2 || p.sy < -2 || p.sx > W + 2 || p.sy > H + 2) continue;
          const tw = 0.75 + 0.25 * Math.sin(e.now / (1400 + st.s * 1800) + st.s * TAU);
          ctx.globalAlpha = (st.band ? 0.25 + st.m * 0.6 : 0.2 + st.m * 0.8) * tw;
          ctx.fillStyle = st.c;
          const r = st.band ? 0.5 + st.m * 0.6 : 0.45 + st.m * 1.1;
          ctx.fillRect(p.sx - r / 2, p.sy - r / 2, r, r);
          if (st.m > 0.75 && !st.band) { ctx.globalAlpha = 0.35 * tw; blit(ctx, glow(st.c, 2.5), p.sx, p.sy, 5); }
        }
        // 近くの塵: 群れの周りに浮かび、寄ると視差で動く
        G.dust ??= (() => { const rnd = seeded(7), R = spread(G) * 1.8, out = []; for (let i = 0; i < 260; i++) { const v = dir(rnd), r = R * Math.cbrt(rnd()); out.push({ x: v.x * r, y: v.y * r, z: v.z * r }); } return out; })();
        ctx.fillStyle = dark ? "#b9c8ff" : "#4a5878";
        for (const pt of G.dust) {
          const p = e.proj(pt);
          if (p.z + G.dist <= 10) continue;
          const far = Math.max(0, Math.min(1, 1.3 - (p.z + G.dist) / (G.dist * 2)));
          ctx.globalAlpha = (dark ? 0.35 : 0.18) * far; ctx.fillRect(p.sx, p.sy, 1, 1);
        }
        // 線: 両端の星の色でつなぐ
        ctx.lineWidth = 0.7;
        ctx.globalCompositeOperation = dark ? "lighter" : "source-over";
        for (const k of e.links) midLine(ctx, k.a, k.b, k.ca, k.cb, 0.3 * k.dep * k.fade, dashOf(e, k.l));
        // 注目している線: 光の帯と、尾を引いて流れる彗星
        for (const s of e.selLinks) {
          ctx.globalAlpha = 1;
          ctx.lineWidth = 6; midLine(ctx, s.from, s.to, s.cf, s.ct, dark ? 0.07 : 0.1, dashOf(e, s.l));
          ctx.lineWidth = 1.2; midLine(ctx, s.from, s.to, s.cf, s.ct, dark ? 0.8 : 0.7, dashOf(e, s.l));
          for (const t of flows(e, s)) {
            const a = Math.sin(Math.PI * t);
            // 尾: 少し前の位置に、だんだん小さく薄い玉を並べる
            for (let i = 7; i >= 1; i--) { const q = at(s, Math.max(0, t - i * 0.012)); ctx.globalAlpha = a * (1 - i / 8) * 0.5; ctx.fillStyle = dark ? whiten(s.ct, 0.6) : s.ct; circle(ctx, q.x, q.y, 1.6 * (1 - i / 9)); }
            const h = at(s, t);
            ctx.globalAlpha = a; blit(ctx, glow(dark ? "#ffffff" : s.ct, 2), h.x, h.y, dark ? 7 : 5);
          }
        }
        // 星: 夜は大きなにじみ・色の光・白い芯、昼は光沢のある色の玉
        for (const d of e.nodes) {
          const a = alphaOf(d), { sx, sy } = d.p, tw = twinkle(e, d, 0.12);
          if (dark) {
            ctx.globalAlpha = a * 0.2 * tw; blit(ctx, glow(d.color, 2.6), sx, sy, d.rad * 7.5);
            ctx.globalAlpha = a * 0.8; blit(ctx, glow(d.color, 1.4), sx, sy, d.rad * 2.3);
            if (d.strong || d.n.deg >= 5) spikes(ctx, sx, sy, d.rad * (3 + Math.min(6, d.n.deg) * 0.5) * tw, whiten(d.color, 0.6), a * 0.5);
            ctx.globalAlpha = a * tw; ctx.fillStyle = "#ffffff"; circle(ctx, sx, sy, d.rad * 0.5);
          } else {
            ctx.globalCompositeOperation = "source-over";
            ctx.globalAlpha = a * 0.3; blit(ctx, glow(d.color, 2), sx, sy, d.rad * 3.2);
            ctx.globalAlpha = a; ctx.fillStyle = d.color; circle(ctx, sx, sy, d.rad);
            ctx.globalAlpha = a * 0.6; ctx.fillStyle = "#ffffff"; circle(ctx, sx - d.rad * 0.3, sy - d.rad * 0.3, d.rad * 0.35);
          }
        }
        ctx.globalCompositeOperation = "source-over";
        for (const d of e.nodes) { ring(e, d, dark ? 6 : 4); if (d.selected) pulse(e, d, dark ? whiten(d.color, 0.4) : d.color); }
      },
      /** 夜は文字を少し青白くして星空になじませる */
      labelColor: (e) => (e.dark ? "#dfe6ff" : e.C.label),
    },

    dust: {
      label: "星屑", note: "色を抜いた細かな点と髪の毛ほどの線だけ。選んだ星とつながる星にだけ色が灯る",
      labelLift: 0.7,
      /** いちばん簡素な案: 無彩色の点と細い線。注目したものだけ種類の色を灯す */
      draw(e) {
        const { ctx, C, dark, W, H } = e, ink = dark ? "#dfe3ea" : "#24282e";
        const bg = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.max(W, H) * 0.7);
        if (dark) { bg.addColorStop(0, "#101114"); bg.addColorStop(1, "#060607"); } else { bg.addColorStop(0, "#fbfaf7"); bg.addColorStop(1, "#efeee9"); }
        ctx.globalAlpha = 1; ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
        ctx.strokeStyle = ink; ctx.lineWidth = 0.45;
        for (const k of e.links) { ctx.globalAlpha = 0.16 * k.dep * k.fade; line(ctx, k.a, k.b, dashOf(e, k.l)); }
        for (const s of e.selLinks) {
          ctx.globalAlpha = 0.6; ctx.lineWidth = 0.8; line(ctx, s.from, s.to, dashOf(e, s.l));
          for (const t of flows(e, s)) { const p = at(s, t); ctx.globalAlpha = Math.sin(Math.PI * t); ctx.fillStyle = s.ct; circle(ctx, p.x, p.y, 1.3); }
        }
        for (const d of e.nodes) {
          const lit = d.strong || d.selected || (e.sel && e.near.has(d.n.id));
          ctx.globalAlpha = alphaOf(d) * (lit ? 1 : 0.85);
          ctx.fillStyle = lit ? d.color : ink;
          circle(ctx, d.p.sx, d.p.sy, Math.max(1, d.rad * (lit ? 0.7 : 0.5)));
          ring(e, d, 3);
        }
      },
      /** 文字も無彩色にそろえる */
      labelColor: (e) => (e.dark ? "#c9ced6" : "#2a2f36"),
    },
  };

  window.STELLA = { styles, hash, glow };
})();
