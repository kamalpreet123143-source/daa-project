#!/usr/bin/env python3
"""
Route Racer - Dijkstra's Shortest Path Game
-------------------------------------------
Run:   python route_racer_game.py
A browser tab opens automatically. The Dijkstra code runs here in Python;
the browser shows the map and the game. Only Python's standard library is used.

Press Ctrl+C in the terminal (or the "Exit" button in the page) to stop.
"""
import heapq
import json
import random
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------
# 1. Graph data (approximate road distances in km)
# ---------------------------------------------------------------
ROADS = [
    ("Delhi", "Chandigarh", 245), ("Delhi", "Jaipur", 280),
    ("Delhi", "Agra", 230),       ("Delhi", "Lucknow", 555),
    ("Agra", "Lucknow", 335),     ("Agra", "Bhopal", 600),
    ("Jaipur", "Ahmedabad", 660), ("Jaipur", "Bhopal", 580),
    ("Ahmedabad", "Mumbai", 525), ("Mumbai", "Pune", 150),
    ("Bhopal", "Nagpur", 350),    ("Nagpur", "Hyderabad", 500),
    ("Nagpur", "Kolkata", 1100),  ("Pune", "Hyderabad", 560),
    ("Pune", "Bengaluru", 840),   ("Hyderabad", "Bengaluru", 575),
    ("Hyderabad", "Chennai", 625), ("Bengaluru", "Chennai", 345),
    ("Lucknow", "Kolkata", 985),  ("Chennai", "Kolkata", 1670),
]

# (longitude, latitude) - only used to draw the map
POSITIONS = {
    "Chandigarh": (76.78, 30.73), "Delhi": (77.10, 28.70),
    "Jaipur": (75.79, 26.91),     "Agra": (78.01, 27.18),
    "Lucknow": (80.95, 26.85),    "Bhopal": (77.41, 23.26),
    "Ahmedabad": (72.57, 23.03),  "Mumbai": (72.88, 19.08),
    "Pune": (73.86, 18.52),       "Nagpur": (79.09, 21.15),
    "Hyderabad": (78.49, 17.39),  "Bengaluru": (77.59, 12.97),
    "Chennai": (80.27, 13.08),    "Kolkata": (88.36, 22.57),
}


def build_graph(roads):
    """Adjacency list: {city: [(neighbour, distance), ...]}"""
    graph = {}
    for a, b, w in roads:
        graph.setdefault(a, []).append((b, w))
        graph.setdefault(b, []).append((a, w))   # undirected
    return graph


# ---------------------------------------------------------------
# 2. Dijkstra's algorithm
# ---------------------------------------------------------------
def dijkstra(graph, source):
    dist = {city: float("inf") for city in graph}
    parent = {city: None for city in graph}
    dist[source] = 0
    pq = [(0, source)]                    # (distance, city)

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:                   # stale entry, skip
            continue
        for v, w in graph[u]:
            if dist[u] + w < dist[v]:     # relaxation
                dist[v] = dist[u] + w
                parent[v] = u
                heapq.heappush(pq, (dist[v], v))
    return dist, parent


def get_path(parent, target):
    path = []
    while target is not None:
        path.append(target)
        target = parent[target]
    return path[::-1]


def dijkstra_trace(graph, source):
    """Same algorithm as dijkstra(), but records every step for the visualiser."""
    dist = {city: float("inf") for city in graph}
    dist[source] = 0
    events = [{"t": "init", "city": source}]
    pq = [(0, source)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            events.append({"t": "skip", "city": u, "d": d})
            continue
        events.append({"t": "visit", "city": u, "d": d})
        for v, w in graph[u]:
            nd = dist[u] + w
            old = dist[v]
            ok = nd < old
            events.append({"t": "relax", "from": u, "to": v, "w": w, "nd": nd,
                           "old": None if old == float("inf") else old, "ok": ok})
            if ok:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    events.append({"t": "done"})
    return events


GRAPH = build_graph(ROADS)
CITIES = sorted(GRAPH)


def solve(src, dst):
    t0 = time.perf_counter()
    dist, parent = dijkstra(GRAPH, src)
    t1 = time.perf_counter()
    return {"src": src, "dst": dst, "path": get_path(parent, dst),
            "dist": dist[dst], "ms": round((t1 - t0) * 1000, 4)}


# Interesting challenges: at least 3 roads between the two cities
def _build_challenges():
    pairs = []
    for s in CITIES:
        _, parent = dijkstra(GRAPH, s)
        for d in CITIES:
            if d != s and len(get_path(parent, d)) >= 4:
                pairs.append((s, d))
    return pairs


CHALLENGES = _build_challenges()


# ---------------------------------------------------------------
# 3. Tiny web server (JSON API + the game page)
# ---------------------------------------------------------------
class Bad(Exception):
    pass


def need_city(q, key):
    value = q.get(key, [""])[0]
    if value not in GRAPH:
        raise Bad(f"Unknown city for '{key}': {value!r}")
    return value


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):          # keep the terminal quiet
        pass

    def _send(self, code, body, ctype):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/":
                self._send(200, PAGE, "text/html; charset=utf-8")
            elif url.path == "/favicon.ico":
                self._send(204, b"", "image/x-icon")
            elif url.path == "/api/graph":
                self._json({"cities": CITIES, "roads": ROADS, "pos": POSITIONS})
            elif url.path == "/api/solve":
                self._json(solve(need_city(q, "src"), need_city(q, "dst")))
            elif url.path == "/api/all":
                src = need_city(q, "src")
                dist, parent = dijkstra(GRAPH, src)
                rows = [{"city": c, "dist": dist[c], "path": get_path(parent, c)}
                        for c in sorted(dist, key=dist.get)]
                self._json({"src": src, "rows": rows})
            elif url.path == "/api/trace":
                src = need_city(q, "src")
                t0 = time.perf_counter()
                events = dijkstra_trace(GRAPH, src)
                ms = round((time.perf_counter() - t0) * 1000, 4)
                out = {"src": src, "events": events, "ms": ms}
                if q.get("dst", [""])[0]:
                    out["result"] = solve(src, need_city(q, "dst"))
                self._json(out)
            elif url.path == "/api/challenge":
                seen = set(q.get("seen", [""])[0].split(";"))
                fresh = [p for p in CHALLENGES if f"{p[0]},{p[1]}" not in seen]
                src, dst = random.choice(fresh or CHALLENGES)
                self._json({"src": src, "dst": dst})
            elif url.path == "/api/hint":
                cur, dst = need_city(q, "cur"), need_city(q, "dst")
                path = solve(cur, dst)["path"]
                self._json({"next": path[1] if len(path) > 1 else None})
            elif url.path == "/api/quit":
                self._json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self._send(404, "Not found", "text/plain; charset=utf-8")
        except Bad as err:
            self._json({"error": str(err)}, 400)


# ---------------------------------------------------------------
# 4. The game page (HTML + CSS + JS)
# ---------------------------------------------------------------
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Route Racer - Dijkstra Game</title>
<style>
:root{
  --bg:#0b1220; --panel:#121b2e; --panel2:#18233b; --line:#2a3b5c; --text:#e6edf7; --muted:#93a4c0;
  --accent:#2dd4bf; --amber:#fbbf24; --green:#4ade80; --red:#fb7185; --blue:#60a5fa;
}
*{box-sizing:border-box}
html,body{margin:0;background:radial-gradient(1200px 700px at 20% -10%,#17284a 0%,var(--bg) 55%);color:var(--text);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;min-height:100%}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 22px;border-bottom:1px solid var(--line)}
h1{font-size:20px;margin:0;letter-spacing:.3px}
h1 span{color:var(--accent)}
.sub{color:var(--muted);font-size:13px;margin-top:2px}
main{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(320px,1fr);gap:16px;padding:16px 22px 28px;max-width:1400px;margin:0 auto}
@media(max-width:960px){main{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}
#mapwrap{padding:6px}
svg{width:100%;height:auto;display:block}
.edge{stroke:#34476b;stroke-width:2;stroke-linecap:round}
.edge.route{stroke:var(--amber);stroke-width:5}
.edge.opt{stroke:var(--green);stroke-width:5;stroke-dasharray:9 7}
.edge.both{stroke:var(--green);stroke-width:6}
.edge.tree{stroke:var(--blue);stroke-width:4}
.edge.scan{stroke:var(--red);stroke-width:5}
.wlabel{font-size:11px;fill:#a9b8d3;text-anchor:middle;paint-order:stroke;stroke:#121b2e;stroke-width:4px;stroke-linejoin:round;pointer-events:none}
.node{cursor:default}
.node circle{fill:#1d2c4a;stroke:#5b7bb0;stroke-width:2.5;transition:fill .2s,stroke .2s}
.node .name{font-size:13px;fill:var(--text);font-weight:600;paint-order:stroke;stroke:#0b1220;stroke-width:4px;stroke-linejoin:round;pointer-events:none}
.node .sub{font-size:12px;fill:var(--amber);font-weight:700;text-anchor:middle;paint-order:stroke;stroke:#0b1220;stroke-width:4px;pointer-events:none}
.node.src circle{fill:#14532d;stroke:var(--green)}
.node.dst circle{fill:#7f1d1d;stroke:var(--red)}
.node.trail circle{fill:#78510c;stroke:var(--amber)}
.node.cur circle{fill:var(--amber);stroke:#fff}
.node.nb circle{stroke:var(--accent);stroke-width:4;animation:pulse 1.1s infinite}
.node.nb{cursor:pointer}
.node.hint circle{fill:var(--accent);stroke:#fff}
.node.settled circle{fill:#14532d;stroke:var(--green)}
.node.frontier circle{fill:#1e3a8a;stroke:var(--blue)}
.node:focus{outline:none}.node:focus circle{stroke:#fff}
.node.play{cursor:pointer}
@keyframes pulse{0%,100%{stroke-opacity:1}50%{stroke-opacity:.25}}
.tabs{display:flex;gap:6px;margin-bottom:12px}
.tabs button{flex:1}
button{font:inherit;color:var(--text);background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:8px 12px;cursor:pointer}
button:hover:not(:disabled){border-color:var(--accent)}
button:disabled{opacity:.45;cursor:not-allowed}
button.primary{background:var(--accent);color:#06241f;border-color:var(--accent);font-weight:700}
button.tab.on{background:var(--accent);color:#06241f;border-color:var(--accent);font-weight:700}
button.danger{border-color:#7f1d1d;color:#fecaca}
select,input[type=range]{font:inherit;color:var(--text);background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:7px 8px;width:100%}
label{font-size:12px;color:var(--muted);display:block;margin:8px 0 4px}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.row>*{flex:1}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}
.stat{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:8px;text-align:center}
.stat b{display:block;font-size:20px}
.stat span{font-size:11px;color:var(--muted)}
.mission{font-size:18px;margin:6px 0}
.mission b.s{color:var(--green)}.mission b.d{color:var(--red)}
.trailtxt{font-size:13px;color:var(--muted);min-height:20px;margin:6px 0}
.msg{min-height:20px;font-size:13px;color:var(--amber)}
.result{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:12px;margin-top:10px}
.stars{font-size:26px;color:var(--amber);letter-spacing:3px}
.big{font-size:34px;font-weight:800;color:var(--accent)}
.muted{color:var(--muted);font-size:13px}
.log{height:210px;overflow:auto;background:#0d1626;border:1px solid var(--line);border-radius:10px;padding:8px;font:12px/1.5 ui-monospace,Consolas,monospace;margin-top:10px}
.log div{border-bottom:1px dashed #1f2d4a;padding:2px 0}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
th,td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.chip{background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:12px}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted);padding:8px 6px 2px}
.legend i{display:inline-block;width:14px;height:4px;border-radius:2px;margin-right:5px;vertical-align:middle}
#bye{position:fixed;inset:0;background:rgba(5,9,18,.92);display:none;align-items:center;justify-content:center;text-align:center;font-size:20px;z-index:9}
</style>
</head>
<body>
<header>
  <div>
    <h1>Route <span>Racer</span> &mdash; Dijkstra's Shortest Path Game</h1>
    <div class="sub">Beat the algorithm: find the shortest road route between Indian cities.</div>
  </div>
  <button class="danger" id="quit">Exit</button>
</header>

<main>
  <section class="card" id="mapwrap">
    <svg id="map" viewBox="0 0 820 700" role="img" aria-label="Road map of cities"></svg>
    <div class="legend" id="legend"></div>
  </section>

  <section class="card">
    <div class="tabs">
      <button class="tab on" data-tab="play">Play</button>
      <button class="tab" data-tab="viz">Watch Dijkstra</button>
      <button class="tab" data-tab="explore">Explorer</button>
    </div>
    <div id="panel"></div>
  </section>
</main>
<div id="bye"><div>Server stopped. You can close this tab.<br><span class="muted">Run the script again to play.</span></div></div>

<script>
"use strict";
const $ = s => document.querySelector(s);
const enc = encodeURIComponent;
const NS = "http://www.w3.org/2000/svg";
let G, ADJ = {}, NODES = {}, EDGES = {}, TAB = "play";

async function api(path){
  const r = await fetch(path);
  const j = await r.json();
  if(!r.ok) throw new Error(j.error || "Request failed");
  return j;
}
function el(tag, attrs, parent){
  const e = document.createElementNS(NS, tag);
  for(const k in attrs) e.setAttribute(k, attrs[k]);
  if(parent) parent.appendChild(e);
  return e;
}
const ekey = (a,b) => a < b ? a+"|"+b : b+"|"+a;
const fmt = n => n.toLocaleString("en-IN");
const esc = s => String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));

function proj(c){
  const [lon, lat] = G.pos[c];
  return [50 + (lon - 72) * (720/17.2), 40 + (30.9 - lat) * (610/18.2)];
}
const LABEL = {Mumbai:"left", Ahmedabad:"left", Jaipur:"left", Delhi:"left", Chandigarh:"right"};

/* ---------- map ---------- */
function buildMap(){
  const svg = $("#map");
  const eg = el("g", {}, svg), ng = el("g", {}, svg);
  for(const [a,b,w] of G.roads){
    const [x1,y1] = proj(a), [x2,y2] = proj(b);
    const line = el("line", {x1,y1,x2,y2,class:"edge"}, eg);
    const t = el("text", {x:(x1+x2)/2, y:(y1+y2)/2+4, class:"wlabel"}, eg);
    t.textContent = w;
    EDGES[ekey(a,b)] = {line, w:t};
  }
  for(const c of G.cities){
    const [x,y] = proj(c);
    const g = el("g", {class:"node", tabindex:0, role:"button", "aria-label":c}, ng);
    el("circle", {cx:x, cy:y, r:14}, g);
    const pos = LABEL[c] || "below";
    const nm = el("text", pos==="left" ? {x:x-20,y:y+5,class:"name","text-anchor":"end"}
                : pos==="right" ? {x:x+20,y:y+5,class:"name","text-anchor":"start"}
                : {x:x,y:y+32,class:"name","text-anchor":"middle"}, g);
    nm.textContent = c;
    const sub = el("text", {x:x, y:y-22, class:"sub"}, g);
    g.addEventListener("click", () => onCity(c));
    g.addEventListener("keydown", e => { if(e.key==="Enter"||e.key===" "){ e.preventDefault(); onCity(c);} });
    NODES[c] = {g, sub};
  }
}
function paint(o){
  o = o || {};
  const nc = o.nodes || {}, ec = o.edges || {}, lb = o.labels || {};
  for(const c of G.cities){
    NODES[c].g.setAttribute("class", "node " + (nc[c] || "") + (o.clickable && nc[c] && nc[c].includes("nb") ? " play" : ""));
    NODES[c].sub.textContent = lb[c] !== undefined ? lb[c] : "";
  }
  for(const k in EDGES){
    EDGES[k].line.setAttribute("class", "edge " + (ec[k] || ""));
    EDGES[k].w.setAttribute("class", "wlabel");
  }
}
function setLegend(items){
  $("#legend").innerHTML = items.map(([col,txt]) => `<span><i style="background:${col}"></i>${txt}</span>`).join("");
}
function onCity(c){
  if(TAB === "play") playMove(c);
  else if(TAB === "viz"){ $("#vSrc").value = c; vizReset(); }
}
function pathEdges(path){ const s = new Set(); for(let i=0;i<path.length-1;i++) s.add(ekey(path[i],path[i+1])); return s; }

/* ---------- tabs ---------- */
function showTab(name){
  vizStop(); TAB = name;
  document.querySelectorAll("button.tab").forEach(b => b.classList.toggle("on", b.dataset.tab === name));
  if(name === "play") playIntro();
  else if(name === "viz") vizInit();
  else exploreInit();
}

/* =========================================================
   PLAY
   ========================================================= */
const P = {active:false, round:0, rounds:5, total:0, scores:[], seen:[], src:null, dst:null,
           route:[], dist:0, hints:0, done:false, hintCity:null, msg:""};

function best(){ try{ return Number(localStorage.getItem("routeRacerBest")||0); }catch(e){ return 0; } }
function saveBest(v){ try{ localStorage.setItem("routeRacerBest", String(v)); }catch(e){} }

function playIntro(){
  P.active = false;
  $("#panel").innerHTML = `
    <h3 style="margin:4px 0 8px">How to play</h3>
    <ol class="muted" style="line-height:1.7;padding-left:18px;margin:0">
      <li>Each round gives you a <b style="color:var(--green)">start</b> and a <b style="color:var(--red)">destination</b> city.</li>
      <li>Click a glowing neighbouring city to drive there. Numbers on roads are distances in km.</li>
      <li>Reach the destination using the <b>shortest total distance</b>. Python's Dijkstra then reveals the true best route.</li>
      <li>Score per round = 100 &times; (best / yours) + 20 for a perfect route &minus; 10 per hint.</li>
    </ol>
    <div class="stats"><div class="stat"><b>${P.rounds}</b><span>rounds</span></div>
      <div class="stat"><b>${best()}</b><span>best score</span></div>
      <div class="stat"><b>${P.rounds*120}</b><span>max score</span></div></div>
    <button class="primary" style="width:100%;padding:12px" id="start">Start game</button>`;
  $("#start").onclick = startGame;
  setLegend([["#4ade80","start"],["#fb7185","destination"],["#fbbf24","your route"],["#4ade80","best route (shown after round)"]]);
  paint();
}
async function startGame(){
  P.round = 0; P.total = 0; P.scores = []; P.seen = [];
  await nextRound();
}
async function nextRound(){
  const ch = await api("/api/challenge?seen=" + enc(P.seen.join(";")));
  P.round++; P.src = ch.src; P.dst = ch.dst; P.route = [ch.src]; P.dist = 0; P.hints = 0;
  P.done = false; P.active = true; P.hintCity = null; P.msg = "";
  P.seen.push(ch.src + "," + ch.dst);
  renderRound();
}
function renderRound(){
  const cur = P.route[P.route.length-1];
  $("#panel").innerHTML = `
    <div class="muted">Round ${P.round} of ${P.rounds}</div>
    <div class="mission">Drive from <b class="s">${P.src}</b> to <b class="d">${P.dst}</b></div>
    <div class="stats">
      <div class="stat"><b id="sDist">${fmt(P.dist)}</b><span>km driven</span></div>
      <div class="stat"><b id="sHint">${P.hints}</b><span>hints used</span></div>
      <div class="stat"><b id="sTotal">${P.total}</b><span>total score</span></div>
    </div>
    <div class="trailtxt" id="trailtxt"></div>
    <div class="msg" id="msg"></div>
    <div class="row" id="ctrl">
      <button id="undo">Undo</button><button id="reset">Restart route</button>
      <button id="hint">Hint (&minus;10)</button>
    </div>
    <div id="result"></div>`;
  $("#undo").onclick = playUndo; $("#reset").onclick = playReset; $("#hint").onclick = playHint;
  paintPlay();
}
function paintPlay(){
  const cur = P.route[P.route.length-1];
  const nodes = {}, edges = {};
  for(const c of P.route) nodes[c] = "trail";
  nodes[P.src] = "src"; nodes[P.dst] = "dst";
  if(!P.done){
    nodes[cur] = (cur === P.src ? "src cur" : "cur");
    for(const n in ADJ[cur]) if(!(n in nodes) || n !== cur) nodes[n] = (nodes[n]||"") + " nb";
    if(P.hintCity) nodes[P.hintCity] = (nodes[P.hintCity]||"") + " hint";
  }
  for(let i=0;i<P.route.length-1;i++) edges[ekey(P.route[i], P.route[i+1])] = "route";
  paint({nodes, edges, clickable:true});
  const t = $("#trailtxt"); if(t) t.textContent = P.route.join(" \u2192 ");
  const sd = $("#sDist"); if(sd) sd.textContent = fmt(P.dist);
  const sh = $("#sHint"); if(sh) sh.textContent = P.hints;
  const st = $("#sTotal"); if(st) st.textContent = P.total;
  const m = $("#msg"); if(m) m.textContent = P.msg;
  ["undo","reset","hint"].forEach(id => { const b = $("#"+id); if(b) b.disabled = P.done || (id!=="hint" && P.route.length<2); });
}
function playMove(c){
  if(!P.active || P.done) return;
  const cur = P.route[P.route.length-1];
  const w = ADJ[cur][c];
  if(w === undefined){
    P.msg = c === cur ? "You are already in " + cur + "." : "No direct road from " + cur + " to " + c + ".";
    paintPlay(); return;
  }
  P.route.push(c); P.dist += w; P.msg = ""; P.hintCity = null;
  if(c === P.dst) finishRound(); else paintPlay();
}
function playUndo(){
  if(P.done || P.route.length < 2) return;
  const last = P.route.pop(), prev = P.route[P.route.length-1];
  P.dist -= ADJ[prev][last]; P.msg = ""; P.hintCity = null; paintPlay();
}
function playReset(){ if(P.done) return; P.route = [P.src]; P.dist = 0; P.msg = ""; P.hintCity = null; paintPlay(); }
async function playHint(){
  if(P.done) return;
  const cur = P.route[P.route.length-1];
  try{
    const h = await api(`/api/hint?cur=${enc(cur)}&dst=${enc(P.dst)}`);
    if(!h.next) return;
    P.hints++; P.hintCity = h.next; P.msg = `Hint: the best way onward from ${cur} is via ${h.next} (\u221210 pts).`;
    paintPlay();
    setTimeout(() => { if(P.hintCity === h.next){ P.hintCity = null; if(!P.done) paintPlay(); } }, 2500);
  }catch(e){ P.msg = e.message; paintPlay(); }
}
async function finishRound(){
  P.done = true;
  const res = await api(`/api/solve?src=${enc(P.src)}&dst=${enc(P.dst)}`);
  const base = Math.round(100 * res.dist / P.dist);
  const perfect = P.dist === res.dist;
  const pts = Math.max(0, base + (perfect ? 20 : 0) - 10 * P.hints);
  const eff = res.dist / P.dist;
  const stars = eff >= 1 ? 3 : eff >= 0.85 ? 2 : eff >= 0.7 ? 1 : 0;
  P.total += pts; P.scores.push(pts);
  const mine = pathEdges(P.route), opt = pathEdges(res.path), edges = {};
  for(const k of mine) edges[k] = opt.has(k) ? "both" : "route";
  for(const k of opt) if(!mine.has(k)) edges[k] = "opt";
  const nodes = {};
  for(const c of res.path) nodes[c] = "trail";
  nodes[P.src] = "src"; nodes[P.dst] = "dst";
  paint({nodes, edges});
  $("#sDist").textContent = fmt(P.dist); $("#sTotal").textContent = P.total;
  ["undo","reset","hint"].forEach(id => $("#"+id).disabled = true);
  $("#msg").textContent = "";
  const last = P.round >= P.rounds;
  const head = perfect ? "Perfect! You matched Dijkstra." : eff >= 0.85 ? "Very close!" : eff >= 0.7 ? "Not bad." : "Dijkstra wins this one.";
  $("#result").innerHTML = `
    <div class="result">
      <div class="stars">${"\u2605".repeat(stars)}${"\u2606".repeat(3-stars)}</div>
      <div style="font-weight:700;margin:4px 0">${head}</div>
      <table>
        <tr><th>Your route</th><td>${esc(P.route.join(" \u2192 "))}<br><b>${fmt(P.dist)} km</b></td></tr>
        <tr><th>Best route</th><td>${esc(res.path.join(" \u2192 "))}<br><b style="color:var(--green)">${fmt(res.dist)} km</b>
            <span class="muted">(Dijkstra in ${res.ms} ms)</span></td></tr>
        <tr><th>Round points</th><td><b>${pts}</b> <span class="muted">= ${base}${perfect ? " + 20 bonus" : ""}${P.hints ? " \u2212 " + 10*P.hints + " hints" : ""}</span></td></tr>
      </table>
      <button class="primary" style="width:100%;margin-top:10px" id="next">${last ? "See final score" : "Next round"}</button>
    </div>`;
  $("#next").onclick = () => last ? showFinal() : nextRound();
}
function showFinal(){
  const max = P.rounds * 120, pct = P.total / max;
  const isBest = P.total > best(); if(isBest) saveBest(P.total);
  const title = pct >= 0.9 ? "Human Dijkstra" : pct >= 0.7 ? "Route Master" : pct >= 0.5 ? "Road Tripper" : "Wandering Traveller";
  P.active = false;
  $("#panel").innerHTML = `
    <div class="result" style="text-align:center">
      <div class="muted">Final score</div>
      <div class="big">${P.total} <span class="muted" style="font-size:16px">/ ${max}</span></div>
      <div style="font-size:18px;font-weight:700;margin:4px 0">${title}</div>
      <div class="muted">${isBest ? "New personal best!" : "Best so far: " + best()}</div>
      <table style="margin-top:10px"><tr><th>Round</th><th>Points</th></tr>
        ${P.scores.map((s,i) => `<tr><td>${i+1}</td><td>${s}</td></tr>`).join("")}</table>
      <button class="primary" style="width:100%;margin-top:12px" id="again">Play again</button>
    </div>`;
  $("#again").onclick = startGame;
  paint();
}

/* =========================================================
   VISUALISER
   ========================================================= */
const V = {events:[], i:0, timer:null, dist:{}, settled:new Set(), cur:null, parent:{}, scan:null, src:null, dst:"", res:null, log:[]};

function cityOptions(sel, extra){
  return (extra ? `<option value="">${extra}</option>` : "") + G.cities.map(c => `<option ${c===sel?"selected":""}>${c}</option>`).join("");
}
function vizInit(){
  $("#panel").innerHTML = `
    <div class="muted">Watch how Dijkstra's algorithm explores the map, one step at a time. You can also click a city on the map to choose the source.</div>
    <label for="vSrc">Source city</label><select id="vSrc">${cityOptions("Delhi")}</select>
    <label for="vDst">Destination (optional)</label><select id="vDst">${cityOptions("", "\u2014 all cities \u2014")}</select>
    <label for="vSpeed">Speed</label><input type="range" id="vSpeed" min="1" max="10" value="6">
    <div class="row"><button class="primary" id="vPlay">Play</button><button id="vStep">Step</button><button id="vReset">Reset</button></div>
    <div class="log" id="vLog"></div>`;
  $("#vSrc").onchange = vizReset; $("#vDst").onchange = vizReset;
  $("#vPlay").onclick = vizToggle; $("#vStep").onclick = vizStepBtn; $("#vReset").onclick = vizReset;
  setLegend([["#60a5fa","reached (tentative)"],["#fbbf24","being processed"],["#4ade80","final (settled)"],["#fb7185","edge being checked"]]);
  vizReset();
}
function vizStop(){ if(V.timer){ clearInterval(V.timer); V.timer = null; } const b = $("#vPlay"); if(b) b.textContent = "Play"; }
function vizReset(){
  vizStop();
  V.events = []; V.i = 0; V.dist = {}; V.settled = new Set(); V.cur = null; V.parent = {}; V.scan = null; V.res = null;
  V.src = $("#vSrc").value; V.dst = $("#vDst").value;
  const lg = $("#vLog"); if(lg) lg.innerHTML = "";
  vizPaint();
}
async function vizLoad(){
  const t = await api(`/api/trace?src=${enc(V.src)}` + (V.dst ? `&dst=${enc(V.dst)}` : ""));
  V.events = t.events; V.res = t.result || null; V.ms = t.ms; V.i = 0;
}
function vizLog(msg){
  const lg = $("#vLog"); if(!lg) return;
  const d = document.createElement("div"); d.textContent = msg; lg.appendChild(d); lg.scrollTop = lg.scrollHeight;
}
function vizApply(e){
  const D = c => V.dist[c] === undefined ? "\u221e" : V.dist[c];
  if(e.t === "init"){
    V.dist[e.city] = 0; vizLog(`Start: ${e.city} = 0 km, every other city = \u221e.`);
  }else if(e.t === "visit"){
    V.cur = e.city; V.settled.add(e.city); V.scan = null;
    vizLog(`Take ${e.city} (${e.d} km) from the queue \u2192 its distance is final.`);
  }else if(e.t === "skip"){
    V.scan = null; vizLog(`Take ${e.city} (${e.d} km): outdated entry, skipped.`);
  }else if(e.t === "relax"){
    V.scan = [e.from, e.to];
    if(e.ok){ V.dist[e.to] = e.nd; V.parent[e.to] = e.from; }
    const was = e.old === null ? "\u221e" : e.old;
    vizLog(`Check ${e.from} \u2192 ${e.to}: ${e.nd - e.w} + ${e.w} = ${e.nd} ${e.ok ? "< " + was + " \u2192 update" : "\u2265 " + was + " \u2192 keep"}`);
  }else if(e.t === "done"){
    V.cur = null; V.scan = null;
    if(V.res) vizLog(`Done. Shortest ${V.src} \u2192 ${V.dst}: ${V.res.path.join(" \u2192 ")} = ${V.res.dist} km.`);
    else vizLog("Done. All shortest distances are final (blue lines show the shortest-path tree).");
  }
}
function vizPaint(){
  const nodes = {}, edges = {}, labels = {};
  for(const c in V.dist){ nodes[c] = "frontier"; labels[c] = V.dist[c]; }
  for(const c of V.settled) nodes[c] = "settled";
  if(V.cur) nodes[V.cur] = "cur";
  if(V.src) nodes[V.src] = (nodes[V.src] || "") + " src";
  if(V.dst) nodes[V.dst] = (nodes[V.dst] || "") + " dst";
  for(const c in V.parent) edges[ekey(c, V.parent[c])] = "tree";
  if(V.scan) edges[ekey(V.scan[0], V.scan[1])] = "scan";
  if(V.res && V.i >= V.events.length && V.events.length){
    for(const k of pathEdges(V.res.path)) edges[k] = "opt";
    for(const c of V.res.path) nodes[c] = "trail" + (c===V.src?" src":"") + (c===V.dst?" dst":"");
  }
  paint({nodes, edges, labels});
}
async function vizStepOnce(){
  if(!V.events.length){ try{ await vizLoad(); }catch(e){ vizLog(e.message); return false; } }
  if(V.i >= V.events.length){ vizStop(); return false; }
  vizApply(V.events[V.i++]);
  vizPaint();
  if(V.i >= V.events.length) vizStop();
  return true;
}
async function vizStepBtn(){ vizStop(); await vizStepOnce(); }
async function vizToggle(){
  if(V.timer){ vizStop(); return; }
  if(V.events.length && V.i >= V.events.length) vizReset();
  if(!V.events.length){ try{ await vizLoad(); }catch(e){ vizLog(e.message); return; } }
  $("#vPlay").textContent = "Pause";
  const delay = () => 1150 - Number($("#vSpeed").value) * 100;
  const tick = async () => {
    const ok = await vizStepOnce();
    if(ok && V.timer) { clearInterval(V.timer); V.timer = setInterval(tick, delay()); }
  };
  V.timer = setInterval(tick, delay());
}

/* =========================================================
   EXPLORER (menu options 1-3 of the console program)
   ========================================================= */
function exploreInit(){
  $("#panel").innerHTML = `
    <div class="muted">List of cities</div>
    <div class="chips">${G.cities.map(c => `<span class="chip">${c}</span>`).join("")}</div>
    <label for="eSrc">Source city</label><select id="eSrc">${cityOptions("Delhi")}</select>
    <label for="eDst">Destination</label><select id="eDst">${cityOptions("Chennai", "\u2014 all cities \u2014")}</select>
    <div class="row"><button class="primary" id="eGo">Find shortest path</button></div>
    <div id="eOut"></div>`;
  $("#eGo").onclick = exploreGo;
  setLegend([["#4ade80","shortest route"],["#60a5fa","shortest-path tree"]]);
  paint(); exploreGo();
}
async function exploreGo(){
  const src = $("#eSrc").value, dst = $("#eDst").value, out = $("#eOut");
  try{
    if(dst){
      const r = await api(`/api/solve?src=${enc(src)}&dst=${enc(dst)}`);
      const nodes = {}; for(const c of r.path) nodes[c] = "trail"; nodes[src] = "src"; nodes[dst] = "dst";
      const edges = {}; for(const k of pathEdges(r.path)) edges[k] = "opt";
      paint({nodes, edges});
      out.innerHTML = `<div class="result"><table>
        <tr><th>Path</th><td>${esc(r.path.join(" \u2192 "))}</td></tr>
        <tr><th>Distance</th><td><b>${fmt(r.dist)} km</b></td></tr>
        <tr><th>Time</th><td>${r.ms} ms</td></tr></table></div>`;
    }else{
      const r = await api(`/api/all?src=${enc(src)}`);
      const edges = {}, nodes = {};
      for(const row of r.rows){ for(const k of pathEdges(row.path)) edges[k] = "tree"; nodes[row.city] = "settled"; }
      nodes[src] = "src";
      const labels = {}; for(const row of r.rows) labels[row.city] = row.dist;
      paint({nodes, edges, labels});
      out.innerHTML = `<table><tr><th>City</th><th>Distance</th><th>Path</th></tr>` +
        r.rows.map(x => `<tr><td>${x.city}</td><td>${fmt(x.dist)} km</td><td>${esc(x.path.join(" \u2192 "))}</td></tr>`).join("") + `</table>`;
    }
  }catch(e){ out.textContent = e.message; }
}

/* ---------- start ---------- */
$("#quit").onclick = async () => {
  try{ await api("/api/quit"); }catch(e){}
  $("#bye").style.display = "flex";
};
document.querySelectorAll("button.tab").forEach(b => b.onclick = () => showTab(b.dataset.tab));
(async () => {
  G = await api("/api/graph");
  for(const c of G.cities) ADJ[c] = {};
  for(const [a,b,w] of G.roads){ ADJ[a][b] = w; ADJ[b][a] = w; }
  buildMap();
  showTab("play");
})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------
# 5. Start the server and open the browser
# ---------------------------------------------------------------
def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)   # port 0 = any free port
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print("=" * 52)
    print(" Route Racer - Dijkstra game")
    print(f" Open in browser: {url}")
    print(" Press Ctrl+C here to stop the game.")
    print("=" * 52)
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("Game stopped. Thank you!")


if __name__ == "__main__":
    main()