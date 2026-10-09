"use strict";
// ネットワークの 5 つの見た目の描き方。毎コマ graph.ts が計算した玉・線を受け取り、見た目ごとに地・線・流れる光・星の順に描く。
// starlight・deep の線は両端の色の中間の単色で 1 本ずつ引き、光の玉と光条は色ごとに一度だけ絵に焼いて置く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 透視の基準の長さ */
    MindmapPreview.FOCAL = 700;
    /** 線の種類 → 見た目（実線・点線・破線・一点鎖線） */
    MindmapPreview.LINK_DASH = {
        depends: [],
        related: [1.5, 3],
        source: [6, 4],
        for: [10, 3, 2, 3],
    };
    const TAU = Math.PI * 2;
    /** 線の上を玉が流れる 1 周の時間（ms） */
    const FLOW_PERIOD = 4200;
    /** 星のまたたきの周期（ms） */
    const TWINKLE_PERIOD = 1900;
    /** 選んだ星から広がる輪の周期（ms） */
    const PULSE_PERIOD = 3600;
    /** 光の玉・光条の絵の一辺（px） */
    const SPRITE = 128;
    /** 光条の絵の筋の太さ（px） */
    const RAY_WIDTH = 3;
    /** 光の玉の絵の、減衰の曲線を近似する段数 */
    const GLOW_STEPS = 12;
    /** 星屑の点の半径の上限（px） */
    const DUST_MAX = 2.6;
    /** 星屑の灯る星の半径の上限（px） */
    const DUST_LIT_MAX = 3.8;
    /** 手前すぎて描かない深さ */
    const NEAR_CLIP = 10;
    /** 見た目ごとの、名前を玉の上へ持ち上げる倍率（星図は星が小さいので少し高く） */
    MindmapPreview.LABEL_LIFT = { constellation: 1.1 };
    // ───── 小さな道具 ─────
    /** 文字列から 0〜1 の決まった値を作る（玉ごとのまたたきの位相に使う） */
    function hashUnit(text) {
        let hash = 2166136261;
        for (const char of text)
            hash = Math.imul(hash ^ (char.codePointAt(0) ?? 0), 16777619);
        return ((hash >>> 0) % 10000) / 10000;
    }
    MindmapPreview.hashUnit = hashUnit;
    /** 種を決めた乱数を返す（空の星の配置を毎回同じにする） */
    function seeded(seed) {
        let a = seed;
        return () => {
            a = (a + 0x6d2b79f5) | 0;
            let t = Math.imul(a ^ (a >>> 15), 1 | a);
            t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    }
    /** `#rrggbb` を `[r, g, b]` にする */
    function rgb(hex) {
        const [r, g, b] = [1, 3, 5].map((start) => Number.parseInt(hex.slice(start, start + 2), 16));
        return [r ?? 0, g ?? 0, b ?? 0];
    }
    /** `#rrggbb` に透明度を付けた色を返す */
    function rgba(hex, alpha) {
        const [r, g, b] = rgb(hex);
        return `rgba(${r},${g},${b},${alpha})`;
    }
    /** `[r, g, b]` を `#rrggbb` にする */
    function toHex(channels) {
        return `#${channels.map((value) => Math.round(value).toString(16).padStart(2, "0")).join("")}`;
    }
    /** 色を白へ寄せる（星の芯の色に使う） */
    function whiten(hex, ratio) {
        return toHex(rgb(hex).map((value) => value + (255 - value) * ratio));
    }
    /** 両端の星の色（`#rrggbb`）の、成分ごとの平均を四捨五入した色を返す */
    function midColor({ from, to }) {
        const a = rgb(from);
        const b = rgb(to);
        return toHex(a.map((value, position) => (value + (b[position] ?? 0)) / 2));
    }
    MindmapPreview.midColor = midColor;
    /** 中心が明るく外へ薄れる光の玉の絵を、色と減衰ごとに一度だけ作って返す */
    const glowCache = new Map();
    function bakeGlow({ color, falloff }) {
        const key = `${color}|${falloff}`;
        const cached = glowCache.get(key);
        if (cached !== undefined)
            return cached;
        const image = document.createElement("canvas");
        image.width = image.height = SPRITE;
        const context = image.getContext("2d");
        const half = SPRITE / 2;
        const gradient = context.createRadialGradient(half, half, 0, half, half, half);
        const [r, g, b] = rgb(color);
        // 減衰の曲線 (1 − t)^falloff を段で近似する
        for (let step = 0; step <= GLOW_STEPS; step += 1) {
            const t = step / GLOW_STEPS;
            gradient.addColorStop(t, `rgba(${r},${g},${b},${(1 - t) ** falloff})`);
        }
        context.fillStyle = gradient;
        context.fillRect(0, 0, SPRITE, SPRITE);
        glowCache.set(key, image);
        return image;
    }
    MindmapPreview.bakeGlow = bakeGlow;
    /** 十字の光の筋の絵を、色ごとに一度だけ作って返す（毎コマはグラデーションを作らず置くだけにする） */
    const rayCache = new Map();
    function bakeRay(color) {
        const cached = rayCache.get(color);
        if (cached !== undefined)
            return cached;
        const image = document.createElement("canvas");
        image.width = image.height = SPRITE;
        const context = image.getContext("2d");
        const half = SPRITE / 2;
        for (const [dx, dy] of [
            [1, 0],
            [0, 1],
        ]) {
            const gradient = context.createLinearGradient(half - dx * half, half - dy * half, half + dx * half, half + dy * half);
            gradient.addColorStop(0, rgba(color, 0));
            gradient.addColorStop(0.5, rgba(color, 1));
            gradient.addColorStop(1, rgba(color, 0));
            context.fillStyle = gradient;
            context.fillRect(dx === 1 ? 0 : half - RAY_WIDTH / 2, dy === 1 ? 0 : half - RAY_WIDTH / 2, dx === 1 ? SPRITE : RAY_WIDTH, dy === 1 ? SPRITE : RAY_WIDTH);
        }
        rayCache.set(color, image);
        return image;
    }
    MindmapPreview.bakeRay = bakeRay;
    /** 焼いた絵を、中心と半径を指定して置く */
    function blit({ context, image, x, y, radius }) {
        context.drawImage(image, x - radius, y - radius, radius * 2, radius * 2);
    }
    /** 2 点を結ぶ線を引く（`dash` は線の種類の見分け） */
    function line({ context, from, to, dash }) {
        context.setLineDash(dash);
        context.beginPath();
        context.moveTo(from.x, from.y);
        context.lineTo(to.x, to.y);
        context.stroke();
    }
    /** 塗りの円を描く */
    function circle({ context, x, y, radius }) {
        context.beginPath();
        context.arc(x, y, radius, 0, TAU);
        context.fill();
    }
    /** 4 方向へとがった星の形（アストロイド）を塗る */
    function star4({ context, x, y, radius }) {
        context.beginPath();
        context.moveTo(x, y - radius);
        context.quadraticCurveTo(x, y, x + radius, y);
        context.quadraticCurveTo(x, y, x, y + radius);
        context.quadraticCurveTo(x, y, x - radius, y);
        context.quadraticCurveTo(x, y, x, y - radius);
        context.fill();
    }
    /** 明るい星の光条（十字の光の筋）を、焼いた絵を長さに合わせて置いて描く */
    function spikes({ context, x, y, length, color, alpha }) {
        context.globalAlpha = alpha;
        blit({ context, image: bakeRay(color), x, y, radius: length });
    }
    /** 注目している線の上を流れる玉の位置（0〜1）を、1 本に 2 つずつ返す。動きを減らす設定では流さない */
    function flows({ frame, position }) {
        if (frame.reducedMotion)
            return [];
        return [0, 0.5].map((offset) => (frame.now / FLOW_PERIOD + offset + (position % 7) * 0.13) % 1);
    }
    /** 線の位置 t の画面座標を返す */
    function at({ link, t }) {
        return { x: link.from.x + (link.to.x - link.from.x) * t, y: link.from.y + (link.to.y - link.from.y) * t };
    }
    /** 選んだ玉・カーソルを乗せた玉に輪を付ける */
    function ring({ frame, star, gap = 4 }) {
        if (!star.selected && !star.hover)
            return;
        const { context } = frame;
        context.setLineDash([]);
        context.globalAlpha = 0.9;
        context.strokeStyle = frame.colors.ring;
        context.lineWidth = 1.5;
        context.beginPath();
        context.arc(star.x, star.y, star.radius + gap, 0, TAU);
        context.stroke();
    }
    /** 星のまたたき（ゆっくり明るさが揺れる）。動きを減らす設定では揺れの中ほどの明るさで止める */
    function twinkle({ frame, star, amplitude }) {
        if (frame.reducedMotion)
            return 1 - amplitude;
        return 1 - amplitude + amplitude * Math.sin(frame.now / TWINKLE_PERIOD + star.seed * TAU);
    }
    /** 選んだ玉から、ゆっくり広がって消える輪を描く。動きを減らす設定では描かない */
    function pulse({ frame, star, color }) {
        if (frame.reducedMotion)
            return;
        const phase = (frame.now % PULSE_PERIOD) / PULSE_PERIOD;
        const { context } = frame;
        context.setLineDash([]);
        context.globalAlpha = (1 - phase) ** 2 * 0.55;
        context.strokeStyle = color;
        context.lineWidth = 1;
        context.beginPath();
        context.arc(star.x, star.y, star.radius * (1.4 + phase * 5), 0, TAU);
        context.stroke();
    }
    /** 両端の星の色の中間の単色で線を 1 本引く（線ごとのグラデーションは作らない） */
    function midLine({ context, link, alpha }) {
        context.strokeStyle = rgba(midColor({ from: link.fromColor, to: link.toColor }), alpha);
        line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
    }
    /** 玉が見える深さか（手前すぎない） */
    function visible(depth) {
        return depth > NEAR_CLIP;
    }
    /** 球面の一様な向きを返す */
    function randomDirection(random) {
        const u = random() * 2 - 1;
        const theta = random() * TAU;
        const s = Math.sqrt(1 - u * u);
        return { x: s * Math.cos(theta), y: u, z: s * Math.sin(theta) };
    }
    /** 深宇宙の空の素材（星の向き・明るさ・色、天の川の帯、星雲の絵）を、種を決めた乱数で一度だけ作って返す（2 回目からは同じもの） */
    let skyCache = null;
    function deepSky() {
        if (skyCache !== null)
            return skyCache;
        const random = seeded(20261002);
        const tints = ["#ffffff", "#cfe0ff", "#fff1d6", "#ffd9c2", "#d9f2ff"];
        const stars = [];
        // 遠い星: 空全体に散らし、暗い星ほど多くする
        for (let i = 0; i < 900; i += 1) {
            const direction = randomDirection(random);
            stars.push({ ...direction, magnitude: random() ** 3, color: tints[Math.floor(random() * tints.length)] ?? "#ffffff", seed: random(), band: false });
        }
        // 天の川: 傾けた大円のまわりに、緯度方向へ正規分布で寄せて置く
        const tilt = 0.5;
        for (let i = 0; i < 1600; i += 1) {
            const angle = random() * TAU;
            const latitude = (random() + random() + random() - 1.5) * 0.16;
            const x = Math.cos(angle) * Math.cos(latitude);
            const y0 = Math.sin(latitude);
            const z0 = Math.sin(angle) * Math.cos(latitude);
            stars.push({
                x,
                y: y0 * Math.cos(tilt) - z0 * Math.sin(tilt),
                z: y0 * Math.sin(tilt) + z0 * Math.cos(tilt),
                magnitude: random() ** 2.5 * 0.8,
                color: tints[Math.floor(random() * 3)] ?? "#ffffff",
                seed: random(),
                band: true,
            });
        }
        // 星雲: 色のにじみを重ねた絵を 4 枚作り、正四面体の 4 方向に貼る（どちらを向いても 1 枚は見える）
        const palettes = [
            ["#2dd4bf", "#6366f1", "#0ea5e9"],
            ["#a855f7", "#ec4899", "#6366f1"],
            ["#14b8a6", "#22d3ee", "#8b5cf6"],
            ["#6366f1", "#0ea5e9", "#a855f7"],
        ];
        const k3 = 1 / Math.sqrt(3);
        const anchors = [
            { x: k3, y: k3, z: k3 },
            { x: -k3, y: -k3, z: k3 },
            { x: -k3, y: k3, z: -k3 },
            { x: k3, y: -k3, z: -k3 },
        ];
        const nebulae = palettes.map((palette, position) => {
            const image = document.createElement("canvas");
            image.width = image.height = 512;
            const context = image.getContext("2d");
            context.globalCompositeOperation = "lighter";
            // 大小のにじみを 14 個重ねて雲の形にする
            for (let i = 0; i < 14; i += 1) {
                const cx = 256 + (random() - 0.5) * 260;
                const cy = 256 + (random() - 0.5) * 200;
                const radius = 60 + random() * 170;
                const color = palette[i % palette.length] ?? "#ffffff";
                const gradient = context.createRadialGradient(cx, cy, 0, cx, cy, radius);
                gradient.addColorStop(0, rgba(color, 0.22 + random() * 0.14));
                gradient.addColorStop(1, rgba(color, 0));
                context.fillStyle = gradient;
                context.fillRect(0, 0, 512, 512);
            }
            return { image, direction: anchors[position], scale: 1.5 + position * 0.2 };
        });
        skyCache = { stars, nebulae };
        return skyCache;
    }
    MindmapPreview.deepSky = deepSky;
    /** 無限に遠い向きを画面へ写す（回転だけ。手前側に無ければ null） */
    function projectDirection({ frame, direction }) {
        const q = frame.rotate(direction);
        return q.z <= 0.02 ? null : { x: frame.width / 2 + (q.x / q.z) * MindmapPreview.FOCAL, y: frame.height / 2 + (q.y / q.z) * MindmapPreview.FOCAL, z: q.z };
    }
    /** 近くの塵: 群れの周りに浮かび、寄ると視差で動く。単位球の中に 260 個を一度だけ置く */
    let dustCache = null;
    function dustCloud() {
        if (dustCache !== null)
            return dustCache;
        const random = seeded(7);
        dustCache = Array.from({ length: 260 }, () => {
            const direction = randomDirection(random);
            const radius = Math.cbrt(random());
            return { x: direction.x * radius, y: direction.y * radius, z: direction.z * radius };
        });
        return dustCache;
    }
    /** 見た目と、ライト / ダークの組ごとの、名前の文字の色を返す。`deep` の夜は星空になじむ青白、`dust` は無彩色、ほかは `fallback`（`tokens.css` の名前の色） */
    function lookLabelColor({ look, dark, fallback }) {
        if (look === "deep")
            return dark ? "#dfe6ff" : fallback;
        if (look === "dust")
            return dark ? "#c9ced6" : "#2a2f36";
        return fallback;
    }
    MindmapPreview.lookLabelColor = lookLabelColor;
    // ───── 見た目ごとの描き方 ─────
    /** `glow`: 今の円に、やわらかい光のにじみを足す。夜は光を足し合わせて明るく重ねる */
    function drawGlow(frame) {
        const { context, colors, dark } = frame;
        context.lineWidth = 0.6;
        context.strokeStyle = colors.line;
        for (const link of frame.links) {
            context.globalAlpha = (dark ? 0.3 : 0.22) * link.alpha;
            line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
        }
        for (const [position, link] of frame.focusLinks.entries()) {
            context.globalAlpha = 1;
            context.strokeStyle = colors.line;
            context.lineWidth = 1;
            line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
            if (dark)
                context.globalCompositeOperation = "lighter";
            for (const t of flows({ frame, position })) {
                const spot = at({ link, t });
                context.globalAlpha = Math.sin(Math.PI * t);
                blit({ context, image: bakeGlow({ color: colors.dot, falloff: 1.8 }), x: spot.x, y: spot.y, radius: 7 });
            }
            context.globalCompositeOperation = "source-over";
        }
        for (const star of frame.stars) {
            if (dark)
                context.globalCompositeOperation = "lighter";
            context.globalAlpha = star.alpha * (dark ? 0.4 : 0.22);
            blit({ context, image: bakeGlow({ color: star.color, falloff: 2 }), x: star.x, y: star.y, radius: star.radius * 3.4 });
            context.globalCompositeOperation = "source-over";
            context.globalAlpha = star.alpha;
            context.fillStyle = star.color;
            circle({ context, x: star.x, y: star.y, radius: star.radius });
            if (dark) {
                context.globalAlpha = star.alpha * 0.55;
                context.fillStyle = "#ffffff";
                circle({ context, x: star.x, y: star.y, radius: star.radius * 0.35 });
            }
            ring({ frame, star });
        }
    }
    /** `starlight`: 夜は白い芯と色のにじみと光条、昼は 4 方向にとがった星形 */
    function drawStarlight(frame) {
        const { context, colors, dark } = frame;
        context.lineWidth = 0.7;
        if (dark)
            context.globalCompositeOperation = "lighter";
        for (const link of frame.links) {
            if (dark) {
                midLine({ context, link, alpha: 0.2 * link.alpha });
            }
            else {
                context.strokeStyle = colors.line;
                context.globalAlpha = 0.22 * link.alpha;
                line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
            }
        }
        context.globalAlpha = 1;
        for (const [position, link] of frame.focusLinks.entries()) {
            context.lineWidth = 1.1;
            if (dark) {
                midLine({ context, link, alpha: 0.75 });
            }
            else {
                context.strokeStyle = colors.line;
                line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
            }
            for (const t of flows({ frame, position })) {
                const spot = at({ link, t });
                context.globalAlpha = Math.sin(Math.PI * t);
                blit({ context, image: bakeGlow({ color: dark ? "#ffffff" : colors.dot, falloff: 2 }), x: spot.x, y: spot.y, radius: dark ? 6 : 4 });
            }
        }
        for (const star of frame.stars) {
            const tw = twinkle({ frame, star, amplitude: 0.18 });
            const big = star.degree >= 4 || star.strong;
            if (dark) {
                context.globalAlpha = star.alpha * 0.28 * tw;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 2.2 }), x: star.x, y: star.y, radius: star.radius * 4.6 });
                context.globalAlpha = star.alpha * 0.95;
                blit({ context, image: bakeGlow({ color: whiten(star.color, 0.25), falloff: 1.3 }), x: star.x, y: star.y, radius: star.radius * 1.8 });
                if (big) {
                    spikes({ context, x: star.x, y: star.y, length: star.radius * (2.4 + Math.min(6, star.degree) * 0.45) * tw, color: whiten(star.color, 0.5), alpha: star.alpha * 0.55 });
                }
                context.globalAlpha = star.alpha * tw;
                context.fillStyle = "#ffffff";
                circle({ context, x: star.x, y: star.y, radius: star.radius * 0.42 });
            }
            else {
                context.globalAlpha = star.alpha * 0.22;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 2 }), x: star.x, y: star.y, radius: star.radius * 2.8 });
                context.globalAlpha = star.alpha;
                context.fillStyle = star.color;
                star4({ context, x: star.x, y: star.y, radius: star.radius * (big ? 1.9 : 1.5) });
            }
            ring({ frame, star, gap: dark ? 5 : 6 });
        }
        context.globalCompositeOperation = "source-over";
    }
    /** `constellation`: 天球の経線・緯線が回転に合わせて回る星図。線は星の手前で切り、選ぶと照準の輪 */
    function drawConstellation(frame) {
        const { context, colors, dark } = frame;
        const sphereRadius = frame.spread * 2.1;
        const grid = dark ? "170,195,255" : "35,55,105";
        // 球の中心までの視点からの距離（奥ほど薄くするのに使う）
        const distance = frame.project({ x: 0, y: 0, z: 0 }).depth;
        // 天球の網: 経線 12 本と緯線 5 本を、奥ほど薄く描く
        context.lineWidth = 0.6;
        /** 球面上の点の列を、奥行きで濃さを変えながらつなぐ */
        const path = ({ points, base }) => {
            for (let i = 1; i < points.length; i += 1) {
                const a = frame.project(points[i - 1]);
                const b = frame.project(points[i]);
                if (!visible(a.depth) || !visible(b.depth))
                    continue;
                const far = Math.max(0.15, Math.min(1, 1.3 - (a.depth + b.depth) / 2 / (distance * 2)));
                context.strokeStyle = `rgba(${grid},${base * far})`;
                line({ context, from: a, to: b, dash: [] });
            }
        };
        const steps = 48;
        for (let meridian = 0; meridian < 12; meridian += 1) {
            const phi = (meridian / 12) * Math.PI;
            const points = [];
            for (let i = 0; i <= steps; i += 1) {
                const theta = (i / steps) * TAU;
                points.push({ x: sphereRadius * Math.cos(theta) * Math.cos(phi), y: sphereRadius * Math.sin(theta), z: sphereRadius * Math.cos(theta) * Math.sin(phi) });
            }
            path({ points, base: dark ? 0.09 : 0.08 });
        }
        for (const latitude of [-60, -30, 0, 30, 60]) {
            const lat = (latitude * Math.PI) / 180;
            const points = [];
            for (let i = 0; i <= steps; i += 1) {
                const phi = (i / steps) * TAU;
                points.push({ x: sphereRadius * Math.cos(lat) * Math.cos(phi), y: sphereRadius * Math.sin(lat), z: sphereRadius * Math.cos(lat) * Math.sin(phi) });
            }
            path({ points, base: latitude === 0 ? (dark ? 0.2 : 0.16) : dark ? 0.09 : 0.08 });
        }
        // 線: 星に触れないよう両端を少し手前で切る
        const ink = dark ? "#c8d4ff" : "#26365e";
        /** 星の半径ぶん両端を詰めた線を引く */
        const gapLine = ({ from, to, fromRadius, toRadius, dash }) => {
            const dx = to.x - from.x;
            const dy = to.y - from.y;
            const length = Math.hypot(dx, dy);
            if (length < fromRadius + toRadius + 4)
                return;
            const ux = dx / length;
            const uy = dy / length;
            context.setLineDash(dash);
            context.beginPath();
            context.moveTo(from.x + ux * (fromRadius + 3), from.y + uy * (fromRadius + 3));
            context.lineTo(to.x - ux * (toRadius + 3), to.y - uy * (toRadius + 3));
            context.stroke();
        };
        /** 玉の半径から、星図の小さく締まった星の半径を求める */
        const starRadius = (point) => (point.radius ?? 0) * 0.55;
        context.strokeStyle = ink;
        context.lineWidth = 0.6;
        for (const link of frame.links) {
            context.globalAlpha = (dark ? 0.32 : 0.3) * link.alpha;
            gapLine({ from: link.from, to: link.to, fromRadius: starRadius(link.from), toRadius: starRadius(link.to), dash: MindmapPreview.LINK_DASH[link.type] });
        }
        const focusStar = frame.stars.find((star) => star.id === frame.focusId);
        for (const [position, link] of frame.focusLinks.entries()) {
            context.globalAlpha = 0.9;
            context.lineWidth = 1.1;
            context.strokeStyle = colors.ring;
            gapLine({ from: link.from, to: link.to, fromRadius: (focusStar === undefined ? 4 : starRadius(focusStar)) + 6, toRadius: starRadius(link.to), dash: MindmapPreview.LINK_DASH[link.type] });
            context.setLineDash([]);
            for (const t of flows({ frame, position })) {
                const spot = at({ link, t });
                context.globalAlpha = 0.9 * Math.sin(Math.PI * t);
                context.fillStyle = colors.ring;
                circle({ context, x: spot.x, y: spot.y, radius: 1.4 });
            }
        }
        // 星: 小さく締まった点と、種類の色の細い輪
        context.setLineDash([]);
        if (dark)
            context.globalCompositeOperation = "lighter";
        for (const star of frame.stars) {
            const radius = star.radius * 0.55;
            if (dark) {
                context.globalAlpha = star.alpha * 0.5;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 3 }), x: star.x, y: star.y, radius: star.radius * 2.4 });
            }
            context.globalAlpha = star.alpha;
            context.fillStyle = dark ? whiten(star.color, 0.7) : ink;
            circle({ context, x: star.x, y: star.y, radius });
            context.globalAlpha = star.alpha * 0.7;
            context.strokeStyle = star.color;
            context.lineWidth = 1;
            context.beginPath();
            context.arc(star.x, star.y, radius + 2.5, 0, TAU);
            context.stroke();
        }
        context.globalCompositeOperation = "source-over";
        // 選んだ星の照準: ゆっくり回る 4 本の目盛りと、点線の外輪。動きを減らす設定では回さない
        for (const star of frame.stars) {
            if (!star.selected && !star.hover)
                continue;
            const radius = star.radius * 0.55 + 8;
            const turn = frame.reducedMotion ? 0 : frame.now / 9000;
            context.globalAlpha = 0.95;
            context.strokeStyle = colors.ring;
            context.lineWidth = 1.2;
            context.beginPath();
            context.arc(star.x, star.y, radius, 0, TAU);
            context.stroke();
            for (let i = 0; i < 4; i += 1) {
                const angle = turn + (i * TAU) / 4;
                context.beginPath();
                context.moveTo(star.x + Math.cos(angle) * (radius + 2), star.y + Math.sin(angle) * (radius + 2));
                context.lineTo(star.x + Math.cos(angle) * (radius + 7), star.y + Math.sin(angle) * (radius + 7));
                context.stroke();
            }
            if (star.selected) {
                context.setLineDash([2, 4]);
                context.globalAlpha = 0.6;
                context.beginPath();
                context.arc(star.x, star.y, radius + 13, 0, TAU);
                context.stroke();
                context.setLineDash([]);
            }
        }
    }
    /** `deep`: 回転に合わせて動く星空・天の川・星雲の地に、光のにじむ星。選ぶと彗星が線を流れ、輪が広がる。昼は夜明けの空 */
    function drawDeep(frame) {
        const { context, dark, width, height } = frame;
        const sky = deepSky();
        // 地: 夜は深い紺から黒へ、昼は淡い青から生成りへ
        const ground = dark
            ? context.createRadialGradient(width / 2, height * 0.45, 0, width / 2, height / 2, Math.max(width, height) * 0.75)
            : context.createLinearGradient(0, 0, 0, height);
        if (dark) {
            ground.addColorStop(0, "#0d1428");
            ground.addColorStop(0.6, "#070a16");
            ground.addColorStop(1, "#030409");
        }
        else {
            ground.addColorStop(0, "#e8edf8");
            ground.addColorStop(0.55, "#f3f1f6");
            ground.addColorStop(1, "#f8f4ec");
        }
        context.globalAlpha = 1;
        context.fillStyle = ground;
        context.fillRect(0, 0, width, height);
        // 星雲: 空の向きに貼ってあり、回すと一緒に流れる
        context.globalCompositeOperation = dark ? "lighter" : "source-over";
        for (const nebula of sky.nebulae) {
            const spot = projectDirection({ frame, direction: nebula.direction });
            if (spot === null)
                continue;
            const size = Math.max(width, height) * nebula.scale;
            context.globalAlpha = (dark ? 0.75 : 0.35) * Math.min(1, spot.z * 2.5);
            context.drawImage(nebula.image, spot.x - size / 2, spot.y - size / 2, size, size);
        }
        // 遠い星と天の川（夜だけ）。ゆっくりまたたく
        if (dark) {
            for (const far of sky.stars) {
                const spot = projectDirection({ frame, direction: far });
                if (spot === null || spot.x < -2 || spot.y < -2 || spot.x > width + 2 || spot.y > height + 2)
                    continue;
                const tw = frame.reducedMotion ? 0.75 : 0.75 + 0.25 * Math.sin(frame.now / (1400 + far.seed * 1800) + far.seed * TAU);
                context.globalAlpha = (far.band ? 0.25 + far.magnitude * 0.6 : 0.2 + far.magnitude * 0.8) * tw;
                context.fillStyle = far.color;
                const size = far.band ? 0.5 + far.magnitude * 0.6 : 0.45 + far.magnitude * 1.1;
                context.fillRect(spot.x - size / 2, spot.y - size / 2, size, size);
                if (far.magnitude > 0.75 && !far.band) {
                    context.globalAlpha = 0.35 * tw;
                    blit({ context, image: bakeGlow({ color: far.color, falloff: 2.5 }), x: spot.x, y: spot.y, radius: 5 });
                }
            }
        }
        // 近くの塵: 群れの周りに浮かび、寄ると視差で動く
        const distance = frame.project({ x: 0, y: 0, z: 0 }).depth;
        const reach = frame.spread * 1.8;
        context.fillStyle = dark ? "#b9c8ff" : "#4a5878";
        for (const dust of dustCloud()) {
            const spot = frame.project({ x: dust.x * reach, y: dust.y * reach, z: dust.z * reach });
            if (!visible(spot.depth))
                continue;
            const far = Math.max(0, Math.min(1, 1.3 - spot.depth / (distance * 2)));
            context.globalAlpha = (dark ? 0.35 : 0.18) * far;
            context.fillRect(spot.x, spot.y, 1, 1);
        }
        // 線: 両端の星の色の中間の単色
        context.lineWidth = 0.7;
        context.globalCompositeOperation = dark ? "lighter" : "source-over";
        for (const link of frame.links)
            midLine({ context, link, alpha: 0.3 * link.alpha });
        // 注目している線: 光の帯と、尾を引いて流れる彗星（動きを減らす設定では強調した線だけ）
        for (const [position, link] of frame.focusLinks.entries()) {
            context.globalAlpha = 1;
            context.lineWidth = 6;
            midLine({ context, link, alpha: dark ? 0.07 : 0.1 });
            context.lineWidth = 1.2;
            midLine({ context, link, alpha: dark ? 0.8 : 0.7 });
            for (const t of flows({ frame, position })) {
                const fade = Math.sin(Math.PI * t);
                // 尾: 少し前の位置に、だんだん小さく薄い玉を並べる
                for (let i = 7; i >= 1; i -= 1) {
                    const tail = at({ link, t: Math.max(0, t - i * 0.012) });
                    context.globalAlpha = fade * (1 - i / 8) * 0.5;
                    context.fillStyle = dark ? whiten(link.toColor, 0.6) : link.toColor;
                    circle({ context, x: tail.x, y: tail.y, radius: 1.6 * (1 - i / 9) });
                }
                const head = at({ link, t });
                context.globalAlpha = fade;
                blit({ context, image: bakeGlow({ color: dark ? "#ffffff" : link.toColor, falloff: 2 }), x: head.x, y: head.y, radius: dark ? 7 : 5 });
            }
        }
        // 星: 夜は大きなにじみ・色の光・白い芯、昼は光沢のある色の玉
        for (const star of frame.stars) {
            const tw = twinkle({ frame, star, amplitude: 0.12 });
            if (dark) {
                context.globalAlpha = star.alpha * 0.2 * tw;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 2.6 }), x: star.x, y: star.y, radius: star.radius * 7.5 });
                context.globalAlpha = star.alpha * 0.8;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 1.4 }), x: star.x, y: star.y, radius: star.radius * 2.3 });
                if (star.strong || star.degree >= 5) {
                    spikes({ context, x: star.x, y: star.y, length: star.radius * (3 + Math.min(6, star.degree) * 0.5) * tw, color: whiten(star.color, 0.6), alpha: star.alpha * 0.5 });
                }
                context.globalAlpha = star.alpha * tw;
                context.fillStyle = "#ffffff";
                circle({ context, x: star.x, y: star.y, radius: star.radius * 0.5 });
            }
            else {
                context.globalCompositeOperation = "source-over";
                context.globalAlpha = star.alpha * 0.3;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 2 }), x: star.x, y: star.y, radius: star.radius * 3.2 });
                context.globalAlpha = star.alpha;
                context.fillStyle = star.color;
                circle({ context, x: star.x, y: star.y, radius: star.radius });
                context.globalAlpha = star.alpha * 0.6;
                context.fillStyle = "#ffffff";
                circle({ context, x: star.x - star.radius * 0.3, y: star.y - star.radius * 0.3, radius: star.radius * 0.35 });
            }
        }
        context.globalCompositeOperation = "source-over";
        for (const star of frame.stars) {
            ring({ frame, star, gap: dark ? 6 : 4 });
            if (star.selected)
                pulse({ frame, star, color: dark ? whiten(star.color, 0.4) : star.color });
        }
    }
    /** `dust`: 色を抜いた細かな点と髪の毛ほどの線だけ。注目の起点とつながる星にだけ種類の色を灯す */
    function drawDust(frame) {
        const { context, dark, width, height } = frame;
        const ink = dark ? "#dfe3ea" : "#24282e";
        const ground = context.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, Math.max(width, height) * 0.7);
        if (dark) {
            ground.addColorStop(0, "#101114");
            ground.addColorStop(1, "#060607");
        }
        else {
            ground.addColorStop(0, "#fbfaf7");
            ground.addColorStop(1, "#efeee9");
        }
        context.globalAlpha = 1;
        context.fillStyle = ground;
        context.fillRect(0, 0, width, height);
        context.strokeStyle = ink;
        context.lineWidth = 0.45;
        for (const link of frame.links) {
            context.globalAlpha = 0.16 * link.alpha;
            line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
        }
        for (const [position, link] of frame.focusLinks.entries()) {
            context.globalAlpha = 0.6;
            context.lineWidth = 0.8;
            line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
            for (const t of flows({ frame, position })) {
                const spot = at({ link, t });
                context.globalAlpha = Math.sin(Math.PI * t);
                context.fillStyle = link.toColor;
                circle({ context, x: spot.x, y: spot.y, radius: 1.3 });
            }
        }
        for (const star of frame.stars) {
            const lit = star.strong || star.selected || (frame.focusId !== null && frame.near.has(star.id));
            context.globalAlpha = star.alpha * (lit ? 1 : 0.85);
            context.fillStyle = lit ? star.color : ink;
            // 寄っても細かな点のままにする（灯る星だけ少し大きく）。名前・輪・鍵もこの点の大きさに合わせて置く
            star.radius = Math.max(1, Math.min(star.radius * (lit ? 0.7 : 0.5), lit ? DUST_LIT_MAX : DUST_MAX));
            circle({ context, x: star.x, y: star.y, radius: star.radius });
            ring({ frame, star, gap: 3 });
        }
    }
    /** 1 コマ分の玉と線を、`look` の見た目で地・線・注目の線を流れる光・星の順に描く（名前・状態の印・鍵・コメントの印は描かない） */
    function drawLook({ look, frame }) {
        frame.context.globalCompositeOperation = "source-over";
        switch (look) {
            case "glow":
                drawGlow(frame);
                break;
            case "starlight":
                drawStarlight(frame);
                break;
            case "constellation":
                drawConstellation(frame);
                break;
            case "deep":
                drawDeep(frame);
                break;
            case "dust":
                drawDust(frame);
                break;
        }
        frame.context.globalCompositeOperation = "source-over";
        frame.context.setLineDash([]);
    }
    MindmapPreview.drawLook = drawLook;
})(MindmapPreview || (MindmapPreview = {}));
