#!/usr/bin/env python3
"""
Geant4 Full Simulation Runner + Live Web Dashboard
===================================================
Cu: 1,2,3,4,5,6 GeV × 300 thicknesses = 1800 sims
Pb: 2,3,4,5,6 GeV   × 300 thicknesses = 1500 sims
Total: 3300 simulations, 100k particles each

Usage:
  source geant4_install/bin/geant4.sh
  python3 runsim_new.py

Dashboard: http://<your-ip>:8080
"""

import subprocess, sys, os, re, shutil, time, json, socket
import multiprocessing, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor, as_completed

# ════════════════════════════════════════════════════════
#  CONFIGURATION — hardcoded as requested
# ════════════════════════════════════════════════════════
# Uruchamiamy wprost z głównego folderu "~/WSL2_Symulacja/"
SIM_BINARY = "./build/GeantSim"
PARTICLES = "100000"
THICKNESS_FROM = 0.1
THICKNESS_TO = 30.0
THICKNESS_STEP = 0.1

# Parallelism
# Zgodnie z życzeniem, twardo zablokowane na 6 równoległych symulacji, każda dostaje 1 rdzeń Geant4.
_CORES = multiprocessing.cpu_count()
PARALLEL_SIMS = 6       # 6 procesów na raz
THREADS_PER_SIM = 1     # 1 wątek na proces Geant4

JOBS = []
# Copper: 2–6 GeV (1 GeV już zrobione u użytkownika)
for e in [2, 3, 4, 5, 6]:
    JOBS.append(("G4_Cu", "Cu", f"{e} GeV"))
# Lead: 2–6 GeV (skip 1 GeV)
for e in [2, 3, 4, 5, 6]:
    JOBS.append(("G4_Pb", "Pb", f"{e} GeV"))

# Generate thickness list once
THICKNESSES = []
v = THICKNESS_FROM
while v <= THICKNESS_TO + 0.0001:
    THICKNESSES.append(round(v, 4))
    v += THICKNESS_STEP

TOTAL_PER_BATCH = len(THICKNESSES)  # 300
TOTAL_BATCHES = len(JOBS)           # 11
TOTAL_SIMS = TOTAL_PER_BATCH * TOTAL_BATCHES  # 3300

# ════════════════════════════════════════════════════════
#  SHARED STATE (read by web server, written by runner)
# ════════════════════════════════════════════════════════
state = {
    "started_at": None,
    "total_sims": TOTAL_SIMS,
    "total_batches": TOTAL_BATCHES,
    "global_done": 0,
    "current_batch_idx": 0,
    "current_batch_label": "",
    "batch_done": 0,
    "batch_total": TOTAL_PER_BATCH,
    "batch_started_at": None,
    "last_thickness": "",
    "last_hits": 0,
    "total_hits": 0,
    "status": "starting",  # starting / running / done
    "output_folder": "",
    "batches": [],  # list of {label, done, total, hits, elapsed_s}
}
state_lock = threading.Lock()

# ════════════════════════════════════════════════════════
#  WEB DASHBOARD
# ════════════════════════════════════════════════════════
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Geant4 — Live Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #09090b;
  --panel: rgba(24, 24, 27, 0.6);
  --border: rgba(255,255,255,0.08);
  --text: #f8fafc;
  --muted: #94a3b8;
  --accent1: #3b82f6;
  --accent2: #8b5cf6;
  --success: #10b981;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  background-color: var(--bg);
  background-image: radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.08), transparent 25%), radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.08), transparent 25%);
  color: var(--text);
  font-family: 'Outfit', sans-serif;
  padding: 40px 24px;
  min-height: 100vh;
}
h1 { font-size: 28px; font-weight: 800; background: linear-gradient(to right, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; letter-spacing: -0.5px; }
.header-wrapper { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 32px; border-bottom: 1px solid var(--border); padding-bottom: 20px; flex-wrap: wrap; gap: 20px;}
.sub { color: var(--muted); font-size: 14px; font-family: 'JetBrains Mono', monospace; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 24px; }
.card {
  background: var(--panel);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 24px -1px rgba(0,0,0,0.5);
  transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 32px -1px rgba(0,0,0,0.6); border-color: rgba(255,255,255,0.15); }
.card h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: var(--muted); margin-bottom: 16px; font-weight: 600; display:flex; justify-content: space-between; }
.big { font-size: 42px; font-weight: 800; line-height: 1; margin-bottom: 8px; font-family: 'JetBrains Mono', monospace; }
.unit { font-size: 16px; color: var(--muted); font-weight: 400; font-family: 'Outfit', sans-serif; }
.bar-wrap { background: rgba(0,0,0,0.4); border-radius: 99px; height: 12px; margin: 16px 0; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); }
.bar-val { height: 100%; border-radius: 99px; transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; }
.bar-global .bar-val { background: linear-gradient(90deg, var(--accent1), var(--accent2)); box-shadow: 0 0 10px rgba(139, 92, 246, 0.5); }
.bar-batch .bar-val { background: linear-gradient(90deg, #10b981, #34d399); box-shadow: 0 0 10px rgba(16, 185, 129, 0.5); }
.bar-val::after { content: ''; position: absolute; top:0; left:0; bottom:0; right:0; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent); animation: shimmer 2s infinite; }
@keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
.info-row { display: flex; justify-content: space-between; color: var(--muted); font-size: 13px; margin-top: 8px; font-family: 'JetBrains Mono', monospace; }
.table-wrap { background: var(--panel); backdrop-filter: blur(12px); border: 1px solid var(--border); border-radius: 16px; padding: 24px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }
th { color: var(--muted); font-weight: 600; padding: 12px 16px; border-bottom: 1px solid var(--border); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
td { padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,0.03); font-family: 'JetBrains Mono', monospace; }
tr:last-child td { border-bottom: none; }
tr.active td { background: rgba(59, 130, 246, 0.05); color: #fff; }
tr.done td { color: var(--success); }
.badge { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
.b-done { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
.b-run { background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.2); animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
.b-wait { background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.pulsing-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; display: inline-block; margin-right: 8px; box-shadow: 0 0 8px #10b981; animation: blink 1.5s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }
.footer { text-align: center; color: var(--muted); font-size: 12px; margin-top: 32px; font-family: 'JetBrains Mono', monospace; opacity: 0.6; }
</style>
</head>
<body>

<div class="header-wrapper">
  <div>
    <h1>⚛ GEANT4 SIMULATION ENGINE</h1>
    <p class="sub">6 PARALLEL PROCESSES × 1 THREAD | 100k PARTICLES / RUN</p>
  </div>
  <div style="text-align:right">
    <div style="font-size:14px;color:var(--muted);margin-bottom:4px">STATUS</div>
    <div id="top-status" style="font-family:'JetBrains Mono';font-size:14px;color:#10b981;"><span class="pulsing-dot"></span><span id="ts-text">RUNNING</span></div>
  </div>
</div>

<div class="grid">
  <!-- GLOBAL -->
  <div class="card">
    <h2>OVERALL PROGRESS <span id="g-count" style="color:var(--accent1)">0/0</span></h2>
    <div class="big" id="g-pct">0<span class="unit">%</span></div>
    <div class="bar-wrap bar-global"><div class="bar-val" id="g-bar" style="width:0%"></div></div>
    <div class="info-row">
      <span id="g-eta">ETA: calculating…</span>
      <span id="g-rate" style="color:#fff">0 sim/s</span>
    </div>
  </div>

  <!-- BATCH -->
  <div class="card">
    <h2>CURRENT BATCH <span id="b-label" style="color:#10b981">—</span></h2>
    <div class="big" id="b-pct">0<span class="unit">%</span></div>
    <div class="bar-wrap bar-batch"><div class="bar-val" id="b-bar" style="width:0%"></div></div>
    <div class="info-row">
      <span id="b-eta">ETA: —</span>
      <span id="b-count">0/0</span>
    </div>
  </div>

  <!-- STATS -->
  <div class="card">
    <h2>GLOBAL METRICS</h2>
    <div style="margin-bottom:16px;">
      <div class="sub" style="margin-bottom:4px">TOTAL DETECTOR HITS</div>
      <div class="big" id="hits" style="font-size:32px; color:var(--accent2)">0</div>
    </div>
    <div>
      <div class="sub" style="margin-bottom:4px">LATEST SIMULATION</div>
      <div id="last-info" style="font-family:'JetBrains Mono';font-size:13px;color:#fff">Waiting for first result…</div>
    </div>
  </div>
</div>

<div class="table-wrap">
  <h2 style="font-size:14px;font-weight:600;margin-bottom:16px;color:var(--text);letter-spacing:1px">BATCH QUEUE</h2>
  <table>
    <thead><tr><th>ID</th><th>Material</th><th>Energy</th><th>Progress</th><th>Hits</th><th>Elapsed</th><th>Status</th></tr></thead>
    <tbody id="batch-table"></tbody>
  </table>
</div>

<div class="footer">Auto-sync active • Dashboard v2.0 Glass</div>

<script>
function fmt(s){
  if(s<0)s=0; let h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=Math.floor(s%60);
  if(h>0)return h+'h '+m+'m'; if(m>0)return m+'m '+sec+'s'; return sec+'s';
}
function num(n){return n.toLocaleString('pl-PL')}

let lastGlobalDone = 0;
let lastTime = Date.now();

function update(){
  fetch('/api/state').then(r=>r.json()).then(d=>{
    let now = Date.now();
    let dt = (now - lastTime)/1000;
    
    // speed gauge
    let rate = 0;
    if(dt>0 && d.global_done > lastGlobalDone){
      rate = (d.global_done - lastGlobalDone)/dt;
    }
    document.getElementById('g-rate').textContent = rate.toFixed(1) + ' sim/s';
    
    // only update last pointers if we actually process to smooth avg
    if(d.global_done > lastGlobalDone || dt > 3) {
      lastGlobalDone = d.global_done;
      lastTime = now;
    }

    let gp=d.total_sims?Math.round(d.global_done/d.total_sims*100):0;
    document.getElementById('g-pct').innerHTML=gp+'<span class="unit">%</span>';
    document.getElementById('g-bar').style.width=gp+'%';
    document.getElementById('g-count').textContent=num(d.global_done)+' / '+num(d.total_sims);
    document.getElementById('hits').textContent=num(d.total_hits);

    // Global ETA
    if(d.global_done>0 && d.started_at){
      let elapsed=(Date.now()/1000)-d.started_at;
      let avg=elapsed/d.global_done;
      let rem=(d.total_sims-d.global_done)*avg;
      document.getElementById('g-eta').textContent='ETA: '+fmt(rem);
    }

    // Batch
    let bp=d.batch_total?Math.round(d.batch_done/d.batch_total*100):0;
    document.getElementById('b-pct').innerHTML=bp+'<span class="unit">%</span>';
    document.getElementById('b-bar').style.width=bp+'%';
    document.getElementById('b-label').textContent=d.current_batch_label||'—';
    document.getElementById('b-count').textContent=num(d.batch_done)+'/'+num(d.batch_total);

    if(d.batch_done>0 && d.batch_started_at){
      let be=(now/1000)-d.batch_started_at;
      let ba=be/d.batch_done;
      let br=(d.batch_total-d.batch_done)*ba;
      document.getElementById('b-eta').textContent='ETA: '+fmt(br);
    }

    // Last sim
    if(d.last_thickness){
      document.getElementById('last-info').textContent=
        d.current_batch_label+' | '+Number(d.last_thickness).toFixed(2)+' cm → '+num(d.last_hits)+' hits';
    }

    // Table
    let tb=document.getElementById('batch-table');
    tb.innerHTML='';
    d.batches.forEach((b,i)=>{
      let cls=''; let badge='';
      if(i<d.current_batch_idx){cls='done';badge='<span class="badge b-done">DONE</span>'}
      else if(i==d.current_batch_idx && d.status=='running'){cls='active';badge='<span class="badge b-run">RUNNING</span>'}
      else if(d.status=='done'){cls='done';badge='<span class="badge b-done">DONE</span>'}
      else{badge='<span class="badge b-wait">WAITING</span>'}
      
      let parts=b.label.split(' @ ');
      let mat=parts[0]||''; let en=parts[1]||'';
      let prog=b.done+'/'+b.total;
      let t=b.elapsed_s>0?fmt(b.elapsed_s):'—';
      
      tb.innerHTML+=`<tr class="${cls}"><td>#${i+1}</td><td><b style="color:#fff">${mat}</b></td><td><span style="color:var(--accent2)">${en}</span></td><td>${prog}</td><td>${num(b.hits)}</td><td>${t}</td><td>${badge}</td></tr>`;
    });

    if(d.status!='done') {
      setTimeout(update, 1500);
    } else {
      document.getElementById('g-eta').textContent='✔ Completed in '+fmt((Date.now()/1000)-d.started_at);
      document.getElementById('g-rate').textContent='Finished';
      let ts = document.getElementById('top-status');
      ts.innerHTML = '<span style="color:#10b981">✔ COMPLETED</span>';
    }
  }).catch(()=>setTimeout(update,3000));
}
update();
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/state":
            with state_lock:
                data = json.dumps(state)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def start_web_server(port=8080):
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    server.daemon_threads = True
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ════════════════════════════════════════════════════════
#  SIMULATION RUNNER
# ════════════════════════════════════════════════════════

def generate_macro(material, thickness_cm, energy):
    return f"""/run/numberOfThreads {THREADS_PER_SIM}
/det/setTargetMaterial {material}
/det/setTargetThickness {thickness_cm} cm
/run/initialize
/gun/particle e-
/gun/energy {energy}
/run/beamOn {PARTICLES}
"""


def run_single(mac_content, out_folder, unique_id):
    """Run one sim. Returns (csv_path, hits) or (None, 0)."""
    mac_file = os.path.join(out_folder, f"_temp_{unique_id}.mac")
    with open(mac_file, "w") as f:
        f.write(mac_content)

    try:
        result = subprocess.run(
            [SIM_BINARY, mac_file],
            capture_output=True, text=True, timeout=3600
        )
    except subprocess.TimeoutExpired:
        return None, 0
    except FileNotFoundError:
        print(f"\n  \033[31m✗ Binary not found: {SIM_BINARY}\033[0m")
        sys.exit(1)
    finally:
        if os.path.exists(mac_file):
            os.remove(mac_file)

    if result.returncode != 0:
        return None, 0

    match = re.search(r"Results written to\s+['\"]?(.*?\.csv)['\"]?", result.stdout)
    if not match:
        return None, 0

    csv_file = match.group(1)
    total_hits = 0
    try:
        with open(csv_file, "r") as f:
            next(f)
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    total_hits += int(parts[2])
    except Exception:
        pass

    if total_hits == 0:
        if os.path.exists(csv_file):
            os.remove(csv_file)
        return None, 0

    dst = os.path.join(out_folder, os.path.basename(csv_file))
    shutil.move(csv_file, dst)

    # Generate SVG heatmap
    if os.path.exists("visualize_results.py"):
        try:
            subprocess.run(
                [sys.executable, "visualize_results.py", dst],
                capture_output=True, timeout=60
            )
        except Exception:
            pass

    return dst, total_hits


# ════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════

def main():
    if not os.path.exists(SIM_BINARY):
        print(f"\n  \033[31m✗ Binary not found: {SIM_BINARY}\033[0m")
        print(f"  Run: source geant4_install/bin/geant4.sh && ./compile.sh\n")
        sys.exit(1)

    # Create master folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    master = f"Results_Full_{timestamp}"
    os.makedirs(master, exist_ok=True)

    # Master summary CSV
    summary = os.path.join(master, "summary_all.csv")
    summary_lock = threading.Lock()
    with open(summary, "w") as sf:
        sf.write("material;energy;thickness_cm;total_hits\n")

    # Init shared state
    with state_lock:
        state["started_at"] = time.time()
        state["output_folder"] = master
        state["status"] = "running"
        state["batches"] = []
        for mat_code, mat_short, energy in JOBS:
            state["batches"].append({
                "label": f"{mat_short} @ {energy}",
                "done": 0, "total": TOTAL_PER_BATCH,
                "hits": 0, "elapsed_s": 0
            })

    # Start web dashboard
    port = 8080
    start_web_server(port)
    local_ip = get_local_ip()

    # Print header
    print(f"""
\033[36m╔══════════════════════════════════════════════════════════════╗
║         ⚛  GEANT4 FULL SIMULATION RUNNER  ⚛                 ║
╚══════════════════════════════════════════════════════════════╝\033[0m

  Cu: 1,2,3,4,5,6 GeV × 300 = \033[93m1800\033[0m sims
  Pb: 2,3,4,5,6 GeV   × 300 = \033[93m1500\033[0m sims
  Total:                       \033[97m{TOTAL_SIMS}\033[0m sims
  Particles: \033[93m{PARTICLES}\033[0m each
  Parallel:  \033[93m{PARALLEL_SIMS} sims × {THREADS_PER_SIM} threads\033[0m  ({_CORES} cores)
  Output:    \033[90m{master}/\033[0m

\033[32m  ╔════════════════════════════════════════════════════╗
  ║  📊 LIVE DASHBOARD:                                ║
  ║  http://{local_ip}:{port:<24}          ║
  ╚════════════════════════════════════════════════════╝\033[0m
""")

    global_done = 0
    t_start = time.time()

    for batch_idx, (mat_code, mat_short, energy) in enumerate(JOBS):
        sub = os.path.join(master, f"{mat_short}_{energy.replace(' ', '')}")
        os.makedirs(sub, exist_ok=True)

        label = f"{mat_short} @ {energy}"
        batch_start = time.time()
        batch_hits = 0

        with state_lock:
            state["current_batch_idx"] = batch_idx
            state["current_batch_label"] = label
            state["batch_done"] = 0
            state["batch_started_at"] = batch_start

        print(f"  \033[97m[{batch_idx+1}/{TOTAL_BATCHES}]\033[0m "
              f"\033[93m{label}\033[0m  ({TOTAL_PER_BATCH} sims, "
              f"{PARALLEL_SIMS} parallel)")

        # ── Parallel execution of all thicknesses in this batch ──
        def process_thickness(args):
            idx, thick = args
            mac = generate_macro(mat_code, thick, energy)
            csv_path, hits = run_single(mac, sub, f"{batch_idx}_{idx}")
            return idx, thick, csv_path, hits

        batch_done_count = 0
        with ThreadPoolExecutor(max_workers=PARALLEL_SIMS) as pool:
            futures = {
                pool.submit(process_thickness, (i, t)): i
                for i, t in enumerate(THICKNESSES)
            }
            for future in as_completed(futures):
                idx, thick, csv_path, hits = future.result()
                batch_done_count += 1
                global_done += 1

                if csv_path and hits > 0:
                    batch_hits += hits
                    with summary_lock:
                        with open(summary, "a") as sf:
                            sf.write(f"{mat_code};{energy};{thick:.4f};{hits}\n")

                # Update shared state
                with state_lock:
                    state["global_done"] = global_done
                    state["batch_done"] = batch_done_count
                    state["last_thickness"] = f"{thick}"
                    state["last_hits"] = hits
                    state["total_hits"] += hits
                    state["batches"][batch_idx]["done"] = batch_done_count
                    state["batches"][batch_idx]["hits"] = batch_hits

                # Terminal progress
                pct = global_done / TOTAL_SIMS * 100
                elapsed = time.time() - t_start
                avg = elapsed / global_done
                eta = (TOTAL_SIMS - global_done) * avg
                eta_h, eta_m = int(eta // 3600), int((eta % 3600) // 60)
                bar_w = 30
                filled = int(bar_w * global_done / TOTAL_SIMS)
                bar = "█" * filled + "░" * (bar_w - filled)
                sys.stdout.write(
                    f"\r    \033[36m{bar}\033[0m {pct:5.1f}%  "
                    f"{batch_done_count}/{TOTAL_PER_BATCH}  "
                    f"ETA ~{eta_h}h{eta_m:02d}m  "
                )
                sys.stdout.flush()

        batch_elapsed = time.time() - batch_start
        with state_lock:
            state["batches"][batch_idx]["elapsed_s"] = batch_elapsed

        bm = int(batch_elapsed // 60)
        bs = int(batch_elapsed % 60)
        print(f"\n    \033[32m✔\033[0m {batch_hits:,} hits in {bm}m{bs}s\n")

    total_elapsed = time.time() - t_start
    th = int(total_elapsed // 3600)
    tm = int((total_elapsed % 3600) // 60)
    ts = int(total_elapsed % 60)

    with state_lock:
        state["status"] = "done"

    print(f"""
\033[32m══════════════════════════════════════════════════════════════
  ✔ ALL {TOTAL_BATCHES} BATCHES COMPLETE
══════════════════════════════════════════════════════════════\033[0m
  Total time:  \033[97m{th}h {tm}m {ts}s\033[0m
  Total hits:  \033[97m{state['total_hits']:,}\033[0m
  Results:     \033[90m{master}/\033[0m
  Summary:     \033[90m{summary}\033[0m
  Dashboard:   http://{local_ip}:{port}  (still alive)
""")

    # Keep web server alive so user can check final results
    print("  \033[90mPress Ctrl+C to exit.\033[0m")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n  Bye!")


if __name__ == "__main__":
    main()
