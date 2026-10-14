/* Stock chart view - opens whenever a stock is opened anywhere in the dashboard.
 * Data: GET /api/stock_chart?symbol=XYZ  (candles, MAs, volume, FLAG zones, setup levels).
 * Library: TradingView Lightweight Charts v4 (window.LightweightCharts).
 */
(function () {
    "use strict";

    const COLORS = {
        up: "#10b981", down: "#ef4444", text: "#9ca3af", grid: "rgba(255,255,255,0.05)",
        blue: "#3b82f6", orange: "#f59e0b", purple: "#8b5cf6", teal: "#14b8a6", bg: "#0d0e12",
    };
    const MA_DEFS = [
        { key: "sma20", label: "SMA 20", color: "#f5c542", on: true },
        { key: "sma50", label: "SMA 50", color: "#3b82f6", on: true },
        { key: "sma150", label: "SMA 150", color: "#a78bfa", on: false },
        { key: "sma200", label: "SMA 200", color: "#f97316", on: true },
        { key: "ema10", label: "EMA 10", color: "#22d3ee", on: false },
        { key: "ema20", label: "EMA 20", color: "#e879f9", on: false },
    ];

    const state = { chart: null, candles: null, volume: null, volAvg: null, maSeries: {}, payload: null,
                    zonesOn: true, levelsOn: true, rangeBars: 130, raf: null, token: 0, priceLines: [], lastSymbol: null };

    const $ = (id) => document.getElementById(id);
    const fmt = (n, d = 2) => (n === null || n === undefined || isNaN(n)) ? "-" :
        Number(n).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
    const fmtVol = (v) => v >= 1e7 ? (v / 1e7).toFixed(2) + " Cr" : v >= 1e5 ? (v / 1e5).toFixed(2) + " L" :
        v >= 1e3 ? (v / 1e3).toFixed(1) + "K" : String(v);

    function setStatus(msg, isError) {
        const el = $("sc-status");
        el.textContent = msg || "";
        el.style.display = msg ? "flex" : "none";
        el.style.color = isError ? "var(--accent-red)" : "var(--text-secondary)";
    }

    function destroyChart() {
        if (state.raf) cancelAnimationFrame(state.raf);
        state.raf = null;
        if (state.chart) { state.chart.remove(); state.chart = null; }
        state.candles = state.volume = state.volAvg = null;
        state.maSeries = {};
        state.priceLines = [];
    }

    function buildChart() {
        const host = $("sc-chart");
        host.innerHTML = '<canvas id="sc-overlay" style="position:absolute;inset:0;pointer-events:none;z-index:2;"></canvas>';
        const chart = LightweightCharts.createChart(host, {
            width: host.clientWidth, height: host.clientHeight,
            layout: { background: { type: "solid", color: "transparent" }, textColor: COLORS.text, fontFamily: "Outfit, sans-serif" },
            grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
            rightPriceScale: { borderColor: "rgba(255,255,255,0.1)", scaleMargins: { top: 0.06, bottom: 0.26 } },
            timeScale: { borderColor: "rgba(255,255,255,0.1)", rightOffset: 6, timeVisible: false },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        });
        state.chart = chart;
        state.candles = chart.addCandlestickSeries({
            upColor: COLORS.up, downColor: COLORS.down, borderUpColor: COLORS.up, borderDownColor: COLORS.down,
            wickUpColor: COLORS.up, wickDownColor: COLORS.down, priceLineColor: COLORS.down,
        });
        state.volume = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol", lastValueVisible: false, priceLineVisible: false });
        chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.80, bottom: 0 } });
        state.volAvg = chart.addLineSeries({ priceScaleId: "vol", color: "rgba(245,158,11,0.8)", lineWidth: 1,
            lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false });
        MA_DEFS.forEach(d => {
            state.maSeries[d.key] = chart.addLineSeries({ color: d.color, lineWidth: 2, lastValueVisible: d.key === "sma20",
                priceLineVisible: false, crosshairMarkerVisible: false, title: d.key === "sma20" ? "SMA 20" : "", visible: d.on });
        });
        chart.subscribeCrosshairMove(updateLegend);
        return chart;
    }

    function updateLegend(param) {
        const p = state.payload;
        if (!p) return;
        let c = null, v = null;
        if (param && param.time && param.seriesData) {
            c = param.seriesData.get(state.candles);
            v = param.seriesData.get(state.volume);
        }
        if (!c) { const k = p.candles[p.candles.length - 1]; c = k; v = p.volume[p.volume.length - 1]; }
        const dir = c.close >= c.open ? COLORS.up : COLORS.down;
        $("sc-legend").innerHTML = `<span>O <b style="color:${dir}">${fmt(c.open)}</b></span> <span>H <b style="color:${dir}">${fmt(c.high)}</b></span> ` +
            `<span>L <b style="color:${dir}">${fmt(c.low)}</b></span> <span>C <b style="color:${dir}">${fmt(c.close)}</b></span> ` +
            `<span>V <b>${v ? fmtVol(v.value) : "-"}</b></span>`;
    }

    function chip(text, color, title) {
        const s = document.createElement("span");
        s.textContent = text;
        if (title) s.title = title;
        s.style.cssText = `font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;font-family:monospace;` +
            `color:${color};background:${color}22;border:1px solid ${color}55;`;
        return s;
    }

    function renderHeader(p) {
        const d = p.detail || {}, st = p.stats;
        $("sc-symbol").textContent = p.symbol;
        $("sc-company").textContent = d.Company_Name && d.Company_Name !== p.symbol ? d.Company_Name : "";
        const chips = $("sc-chips");
        chips.innerHTML = "";
        if (d.Industry) chips.appendChild(chip(d.Industry + (d.Industry_Rank && d.Industry_Rank !== "N/A" ? ` · #${d.Industry_Rank}` : ""), COLORS.teal, d.Industry_Category || ""));
        if (d.Setup_Found) chips.appendChild(chip((d.Setup_Type || "SETUP").replace(/_/g, " ") + (d.Grade ? ` · ${d.Grade}` : ""), COLORS.up, "Current scan candidate"));
        if (d.MS_Score !== undefined && d.MS_Score !== null) chips.appendChild(chip(`AMS ${d.MS_Score}`, COLORS.purple, "Antigravity Momentum Score"));
        if (st.off_52w_high_pct !== null) chips.appendChild(chip(`${st.off_52w_high_pct}% from 52W high`, COLORS.blue));
        if (st.rvol !== null) chips.appendChild(chip(`RVOL ${st.rvol}x`, st.rvol >= 1.5 ? COLORS.orange : COLORS.text));
        if (p.earnings && p.earnings.date) {
            const dd = p.earnings.days;
            chips.appendChild(chip(`Earnings ${p.earnings.date}${dd !== null && dd >= 0 ? ` (${dd}d)` : ""}`, dd !== null && dd >= 0 && dd <= 7 ? COLORS.red || COLORS.down : COLORS.orange));
        }
        $("sc-price").textContent = "₹" + fmt(st.last);
        const ch = $("sc-change");
        ch.textContent = (st.change_pct >= 0 ? "+" : "") + st.change_pct.toFixed(2) + "%";
        ch.style.color = st.change_pct >= 0 ? COLORS.up : COLORS.down;
        $("sc-asof").textContent = "EOD · NSE cash · " + p.as_of;
    }

    function applyLevels() {
        state.priceLines.forEach(l => state.candles.removePriceLine(l));
        state.priceLines = [];
        const d = state.payload && state.payload.detail;
        if (!state.levelsOn || !d || !d.Setup_Found) return;
        const add = (price, title, color, style) => {
            if (price && price > 0) state.priceLines.push(state.candles.createPriceLine({ price, title, color, lineWidth: 1, lineStyle: style, axisLabelVisible: true }));
        };
        add(d.Trigger_Price, "Entry", COLORS.blue, 2);
        add(d.Stop_Loss, "Stop", COLORS.down, 2);
        add(d.Target_1, "T1", COLORS.up, 1);
        add(d.Target_2, "T2", COLORS.up, 1);
    }

    function applyMarkers() {
        const p = state.payload;
        const first = p.candles[0].time;
        const markers = [];
        (p.zones || []).forEach(z => {
            if (!state.zonesOn || !z.outcome_time || z.outcome_time < first) return;
            if (z.outcome === "BREAKOUT") markers.push({ time: z.outcome_time, position: "belowBar", color: COLORS.up, shape: "arrowUp", text: "BRK" });
            if (z.outcome === "FAILED") markers.push({ time: z.outcome_time, position: "aboveBar", color: COLORS.down, shape: "arrowDown", text: "FAIL" });
        });
        markers.sort((a, b) => (a.time < b.time ? -1 : 1));
        state.candles.setMarkers(markers);
    }

    function setRange(bars) {
        state.rangeBars = bars;
        const n = state.payload.candles.length;
        state.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - bars), to: n + 5 });
    }

    // ---- zone overlay -------------------------------------------------------------------------------------------
    function drawOverlay(ctx, w, h, scale) {
        const p = state.payload;
        if (!p || !state.chart || !state.zonesOn) return;
        const ts = state.chart.timeScale();
        (p.zones || []).forEach(z => {
            const x1 = ts.timeToCoordinate(z.start), x2 = ts.timeToCoordinate(z.end);
            const y1 = state.candles.priceToCoordinate(z.high), y2 = state.candles.priceToCoordinate(z.low);
            if (x1 === null || x2 === null || y1 === null || y2 === null) return;
            const pad = 4, x = Math.min(x1, x2) - pad, wd = Math.abs(x2 - x1) + pad * 2, y = Math.min(y1, y2), ht = Math.abs(y2 - y1);
            const col = z.outcome === "FAILED" ? COLORS.down : z.outcome === "BREAKOUT" ? COLORS.up : COLORS.blue;
            ctx.save();
            ctx.scale(scale, scale);
            ctx.fillStyle = col + "1f";
            ctx.fillRect(x, y, wd, ht);
            ctx.strokeStyle = col + "aa";
            ctx.setLineDash([4, 3]);
            ctx.lineWidth = 1;
            ctx.strokeRect(x, y, wd, ht);
            // label tab
            const label = z.label + (z.outcome === "ACTIVE" ? " · LIVE" : "");
            ctx.setLineDash([]);
            ctx.font = "600 9px Outfit, sans-serif";
            const tw = ctx.measureText(label).width + 8;
            ctx.fillStyle = col + "cc";
            ctx.fillRect(x, y - 13, tw, 12);
            ctx.fillStyle = "#fff";
            ctx.textBaseline = "middle";
            ctx.fillText(label, x + 4, y - 7);
            // breakout trigger line extending right from the zone high
            ctx.strokeStyle = col + "66";
            ctx.setLineDash([2, 3]);
            ctx.beginPath(); ctx.moveTo(x + wd, y); ctx.lineTo(Math.min(x + wd + 80, w), y); ctx.stroke();
            ctx.restore();
        });
    }

    function renderOverlayLoop() {
        const host = $("sc-chart"), cv = $("sc-overlay");
        if (!cv || !state.chart) return;
        const dpr = window.devicePixelRatio || 1, w = host.clientWidth, h = host.clientHeight;
        if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
            cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
            cv.style.width = w + "px"; cv.style.height = h + "px";
            state.chart.applyOptions({ width: w, height: h });
            // Bar spacing is kept across a resize, so re-fit the window to the settled width.
            if (state.payload) setRange(state.rangeBars);
        }
        const ctx = cv.getContext("2d");
        ctx.clearRect(0, 0, cv.width, cv.height);
        drawOverlay(ctx, w, h, dpr);
        state.raf = requestAnimationFrame(renderOverlayLoop);
    }

    // ---- PNG export ---------------------------------------------------------------------------------------------
    function exportPng() {
        if (!state.chart || !state.payload) return;
        const p = state.payload, shot = state.chart.takeScreenshot();
        const host = $("sc-chart"), ratio = shot.width / host.clientWidth;
        const headH = Math.round(64 * ratio), footH = Math.round(24 * ratio);
        const out = document.createElement("canvas");
        out.width = shot.width; out.height = shot.height + headH + footH;
        const g = out.getContext("2d");
        g.fillStyle = COLORS.bg; g.fillRect(0, 0, out.width, out.height);
        g.drawImage(shot, 0, headH);
        // overlay zones at export resolution
        const zoneLayer = document.createElement("canvas");
        zoneLayer.width = shot.width; zoneLayer.height = shot.height;
        drawOverlay(zoneLayer.getContext("2d"), host.clientWidth, host.clientHeight, ratio);
        g.drawImage(zoneLayer, 0, headH);
        // header / footer text
        const d = p.detail || {};
        g.textBaseline = "middle";
        g.fillStyle = "#f3f4f6"; g.font = `700 ${18 * ratio}px Outfit, sans-serif`;
        g.fillText(p.symbol, 14 * ratio, 22 * ratio);
        g.fillStyle = COLORS.text; g.font = `400 ${11 * ratio}px Outfit, sans-serif`;
        g.fillText([d.Company_Name, d.Industry].filter(Boolean).join(" · "), 14 * ratio, 44 * ratio);
        g.textAlign = "right";
        g.fillStyle = "#f3f4f6"; g.font = `700 ${18 * ratio}px Outfit, sans-serif`;
        g.fillText("₹" + fmt(p.stats.last), out.width - 14 * ratio, 22 * ratio);
        g.fillStyle = p.stats.change_pct >= 0 ? COLORS.up : COLORS.down; g.font = `600 ${12 * ratio}px Outfit, sans-serif`;
        g.fillText((p.stats.change_pct >= 0 ? "+" : "") + p.stats.change_pct.toFixed(2) + "%", out.width - 14 * ratio, 44 * ratio);
        g.textAlign = "left";
        g.fillStyle = COLORS.text; g.font = `400 ${10 * ratio}px Outfit, sans-serif`;
        g.fillText(`Minervini OS · EOD · NSE cash segment · data as of ${p.as_of}`, 14 * ratio, headH + shot.height + footH / 2);
        g.textAlign = "right";
        g.fillText("Exported " + new Date().toLocaleString("en-IN"), out.width - 14 * ratio, headH + shot.height + footH / 2);
        out.toBlob(blob => {
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `${p.symbol}_${p.as_of}.png`;
            a.click();
            setTimeout(() => URL.revokeObjectURL(a.href), 2000);
        });
    }

    // ---- open / close -------------------------------------------------------------------------------------------
    function closeChart() {
        $("stock-chart-modal").style.display = "none";
        destroyChart();
        state.payload = null;
        document.removeEventListener("keydown", onKey);
    }
    function onKey(e) { if (e.key === "Escape") closeChart(); }

    async function openStockChart(symbol) {
        if (!symbol) return;
        symbol = String(symbol).trim().toUpperCase();
        if (typeof LightweightCharts === "undefined") {
            // Library blocked (offline / CDN down): fall back to the original detail drawer.
            if (typeof window.showTickerDrawer === "function") window.showTickerDrawer(symbol);
            return;
        }
        const token = ++state.token;
        state.lastSymbol = symbol;
        const modal = $("stock-chart-modal");
        modal.style.display = "flex";
        document.removeEventListener("keydown", onKey);
        document.addEventListener("keydown", onKey);
        destroyChart();
        state.payload = null;
        $("sc-symbol").textContent = symbol;
        ["sc-company", "sc-chips", "sc-price", "sc-change", "sc-legend", "sc-asof"].forEach(id => { $(id).textContent = ""; });
        setStatus("Loading chart…");
        try {
            const r = await fetch(`/api/stock_chart?symbol=${encodeURIComponent(symbol)}`);
            const p = await r.json();
            if (token !== state.token) return;           // a newer open superseded this one
            if (!r.ok || p.error) throw new Error(p.error || "Chart request failed");
            state.payload = p;
            setStatus("");
            buildChart();
            state.candles.setData(p.candles);
            state.volume.setData(p.volume.map(v => ({ time: v.time, value: v.value, color: v.up ? "rgba(16,185,129,0.45)" : "rgba(239,68,68,0.45)" })));
            state.volAvg.setData(p.vol_sma50);
            MA_DEFS.forEach(d => state.maSeries[d.key].setData(p.indicators[d.key] || []));
            renderHeader(p);
            applyLevels();
            applyMarkers();
            setRange(130);
            updateLegend(null);
            buildToggles();
            renderOverlayLoop();
        } catch (e) {
            if (token !== state.token) return;
            console.error("stock chart error:", e);
            setStatus(`Could not load chart for ${symbol}: ${e.message}`, true);
        }
    }

    function buildToggles() {
        const box = $("sc-toggles");
        box.innerHTML = "";
        const mk = (label, color, on, cb) => {
            const b = document.createElement("button");
            b.type = "button";
            b.textContent = label;
            const paint = (active) => { b.style.cssText = `font-size:11px;padding:3px 9px;border-radius:12px;cursor:pointer;font-family:inherit;` +
                `border:1px solid ${active ? color : "var(--border-color)"};background:${active ? color + "26" : "transparent"};color:${active ? color : "var(--text-secondary)"};`; };
            let active = on; paint(active);
            b.onclick = () => { active = !active; paint(active); cb(active); };
            box.appendChild(b);
        };
        MA_DEFS.forEach(d => mk(d.label, d.color, d.on, a => state.maSeries[d.key].applyOptions({ visible: a, lastValueVisible: a && d.key === "sma20" })));
        mk("Zones", COLORS.blue, state.zonesOn, a => { state.zonesOn = a; applyMarkers(); });
        mk("Entry/Stop", COLORS.up, state.levelsOn, a => { state.levelsOn = a; applyLevels(); });
    }

    function init() {
        $("sc-close").onclick = closeChart;
        $("stock-chart-modal").addEventListener("mousedown", e => { if (e.target.id === "stock-chart-modal") closeChart(); });
        $("sc-png").onclick = exportPng;
        $("sc-tv").onclick = () => { if (state.lastSymbol) window.open(`https://www.tradingview.com/chart/?symbol=NSE%3A${encodeURIComponent(state.lastSymbol)}`, "_blank", "noopener"); };
        $("sc-detail").onclick = () => { const s = state.lastSymbol; if (s && typeof window.showTickerDrawer === "function") { closeChart(); window.showTickerDrawer(s); } };
        document.querySelectorAll("[data-sc-range]").forEach(b => b.onclick = () => state.chart && state.payload && setRange(parseInt(b.dataset.scRange, 10)));
    }

    window.openStockChart = openStockChart;
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
