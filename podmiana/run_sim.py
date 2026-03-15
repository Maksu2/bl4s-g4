#!/usr/bin/env python3
"""
Geant4 Full Simulation Runner + Live Web Dashboard
===================================================
Cu: 1,2,3,4,5,6 GeV × 300 thicknesses = 1800 sims
Pb: 2,3,4,5,6 GeV   × 300 thicknesses = 1500 sims
Total: 3300 simulations, 100k particles each
A
Usage:
  source geant4_install/bin/geant4.sh
  python3 run_sim.py

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
SIM_BINARY = "./build/GeantSim"
PARTICLES = "100000"
THICKNESS_FROM = 0.1
THICKNESS_TO = 30.0
THICKNESS_STEP = 0.1

# Parallelism: auto-detect best split
# e.g. 6 cores → 3 parallel sims × 2 Geant4 threads each
# e.g. 10 cores → 5 parallel × 2 threads
# e.g. 12 cores → 4 parallel × 3 threads
_CORES = multiprocessing.cpu_count()
PARALLEL_SIMS = max(1, _CORES // 2)       # how many sims run at once
THREADS_PER_SIM = max(1, _CORES // PARALLEL_SIMS)  # Geant4 threads per sim

JOBS = []
# Copper: 1–6 GeV
for e in [1, 2, 3, 4, 5, 6]:
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
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e2e8f0;font-family:'SF Mono','JetBrains Mono',monospace;padding:24px}
h1{font-size:20px;color:#38bdf8;margin-bottom:4px}
.sub{color:#64748b;font-size:12px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
.card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px}
.card h2{font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#06b6d4;margin-bottom:12px}
.big{font-size:36px;font-weight:800;color:#f8fafc;line-height:1}
.unit{font-size:14px;color:#64748b;font-weight:400}
.bar-bg{background:#0f172a;border-radius:8px;height:18px;margin-top:10px;overflow:hidden}
.bar-fg{height:100%;border-radius:8px;transition:width .5s ease}
.bar-global .bar-fg{background:linear-gradient(90deg,#0ea5e9,#6366f1)}
.bar-batch .bar-fg{background:linear-gradient(90deg,#10b981,#06b6d4)}
.eta{color:#94a3b8;font-size:13px;margin-top:6px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;color:#06b6d4;font-weight:700;text-transform:uppercase;letter-spacing:1px;padding:8px 10px;border-bottom:2px solid #334155}
td{padding:8px 10px;border-bottom:1px solid #1e293b;color:#94a3b8}
tr.active td{color:#f8fafc;background:rgba(56,189,248,.06)}
tr.done td{color:#4ade80}
.status-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;text-transform:uppercase}
.status-done{background:rgba(74,222,128,.15);color:#4ade80}
.status-running{background:rgba(56,189,248,.15);color:#38bdf8}
.status-waiting{background:rgba(100,116,139,.15);color:#64748b}
.footer{text-align:center;color:#334155;font-size:11px;margin-top:24px}
</style>
</head>
<body>
<h1>⚛ GEANT4 SIMULATION DASHBOARD</h1>
<p class="sub">Cu: 1–6 GeV • Pb: 2–6 GeV • 100k particles • 0.1–30 cm</p>

<div class="grid">
  <div class="card">
    <h2>Overall Progress</h2>
    <div class="big" id="g-pct">0<span class="unit">%</span></div>
    <div class="bar-bg bar-global"><div class="bar-fg" id="g-bar" style="width:0%"></div></div>
    <div class="eta" id="g-eta">ETA: calculating…</div>
    <div class="eta" id="g-count">0 / 0 simulations</div>
  </div>
  <div class="card">
    <h2>Current Batch</h2>
    <div class="big" id="b-pct">0<span class="unit">%</span></div>
    <div class="bar-bg bar-batch"><div class="bar-fg" id="b-bar" style="width:0%"></div></div>
    <div class="eta" id="b-label">—</div>
    <div class="eta" id="b-eta">ETA: —</div>
  </div>
  <div class="card">
    <h2>Total Hits</h2>
    <div class="big" id="hits">0</div>
  </div>
  <div class="card">
    <h2>Last Simulation</h2>
    <div class="eta" id="last-info">Waiting…</div>
  </div>
</div>

<div class="card">
<h2>Batch Queue</h2>
<table>
<thead><tr><th>#</th><th>Material</th><th>Energy</th><th>Progress</th><th>Hits</th><th>Time</th><th>Status</th></tr></thead>
<tbody id="batch-table"></tbody>
</table>
</div>

<div class="footer">Auto-refreshes every 2s</div>

<script>
function fmt(s){
  if(s<0)s=0;
  let h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=Math.floor(s%60);
  if(h>0)return h+'h '+m+'m';
  if(m>0)return m+'m '+sec+'s';
  return sec+'s';
}
function num(n){return n.toLocaleString('pl-PL')}
function update(){
  fetch('/api/state').then(r=>r.json()).then(d=>{
    let gp=d.total_sims?Math.round(d.global_done/d.total_sims*100):0;
    document.getElementById('g-pct').innerHTML=gp+'<span class="unit">%</span>';
    document.getElementById('g-bar').style.width=gp+'%';
    document.getElementById('g-count').textContent=num(d.global_done)+' / '+num(d.total_sims)+' simulations';
    document.getElementById('hits').textContent=num(d.total_hits);

    // Global ETA
    if(d.global_done>0 && d.started_at){
      let elapsed=(Date.now()/1000)-d.started_at;
      let avg=elapsed/d.global_done;
      let rem=(d.total_sims-d.global_done)*avg;
      document.getElementById('g-eta').textContent='ETA: '+fmt(rem)+' remaining';
    }

    // Batch
    let bp=d.batch_total?Math.round(d.batch_done/d.batch_total*100):0;
    document.getElementById('b-pct').innerHTML=bp+'<span class="unit">%</span>';
    document.getElementById('b-bar').style.width=bp+'%';
    document.getElementById('b-label').textContent=d.current_batch_label||'—';
    if(d.batch_done>0 && d.batch_started_at){
      let be=(Date.now()/1000)-d.batch_started_at;
      let ba=be/d.batch_done;
      let br=(d.batch_total-d.batch_done)*ba;
      document.getElementById('b-eta').textContent='ETA batch: '+fmt(br);
    }

    // Last sim
    if(d.last_thickness){
      document.getElementById('last-info').textContent=
        d.current_batch_label+' | '+d.last_thickness+' cm → '+num(d.last_hits)+' hits';
    }

    // Table
    let tb=document.getElementById('batch-table');
    tb.innerHTML='';
    d.batches.forEach((b,i)=>{
      let cls='';
      let badge='';
      if(i<d.current_batch_idx){cls='done';badge='<span class="status-badge status-done">done</span>'}
      else if(i==d.current_batch_idx && d.status=='running'){cls='active';badge='<span class="status-badge status-running">running</span>'}
      else if(d.status=='done'){cls='done';badge='<span class="status-badge status-done">done</span>'}
      else{badge='<span class="status-badge status-waiting">waiting</span>'}
      let parts=b.label.split(' @ ');
      let mat=parts[0]||'';
      let en=parts[1]||'';
      let prog=b.done+'/'+b.total;
      let t=b.elapsed_s>0?fmt(b.elapsed_s):'—';
      tb.innerHTML+='<tr class="'+cls+'"><td>'+(i+1)+'</td><td>'+mat+'</td><td>'+en+'</td><td>'+prog+'</td><td>'+num(b.hits)+'</td><td>'+t+'</td><td>'+badge+'</td></tr>';
    });

    if(d.status!='done')setTimeout(update,2000);
    else document.getElementById('g-eta').textContent='✔ Completed in '+fmt((Date.now()/1000)-d.started_at);
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
  ║  http://{local_ip}:{port:<24s}          ║
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
