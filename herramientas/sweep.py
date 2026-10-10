# Uso: sweep.py SEQ "PLANTILLA con {c}" [plantilla2 ...]  -> encuentra el control válido de cada plantilla
import sys, json, time, threading, urllib.request, urllib.error, os
from concurrent.futures import ThreadPoolExecutor
S = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.environ.get("CAJA_TOKEN_FILE", os.path.expanduser("~/.config/caja-negra/token"))
BASE = "https://caja-negra-production-c64f.up.railway.app"
LOG = os.environ.get("CAJA_LOG_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "pruebas", "experimentos.jsonl")
TOKEN = open(TOKEN_FILE).read().strip()
lock = threading.Lock(); rl = threading.Lock(); last = [0.0]
def call(m, seq, hip):
    with rl:
        w = last[0] + 0.17 - time.time()
        if w > 0: time.sleep(w)
        last[0] = time.time()
    body = json.dumps({"m": m}).encode()
    req = urllib.request.Request(BASE + "/msg", data=body, method="POST",
          headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    try: r = urllib.request.urlopen(req, timeout=15); st, raw, h = r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e: st, raw, h = e.code, e.read().decode(), e.headers
    if h.get("X-Frontier-Infra"): raise SystemExit("RATE LIMIT")
    resp = json.loads(raw)
    xr = h.get("X-Req")
    with lock:
        n = sum(1 for _ in open(LOG)) + 1
        open(LOG, "a").write(json.dumps({"id": n, "seq": seq, "x_req": int(xr) if xr and xr.isdigit() else xr,
            "hipotesis": hip, "request": {"m": m}, "status": st, "response": resp}, ensure_ascii=False) + "\n")
    return st, resp
seq = sys.argv[1]
def find(tpl):
    hip = f"barrido de control para '{tpl}': buscar el único valor que no da E202"
    found = []
    def one(c):
        if found: return
        st, resp = call(tpl.format(c=c), seq, hip)
        if not (st == 400 and resp.get("error") == "E202"): found.append((c, st, resp))
    tried = set()
    for l in open(LOG):
        d = json.loads(l)
        m = d["request"].get("m") if isinstance(d["request"], dict) else None
        if d["seq"] == seq and m and m.rsplit(";", 1)[0] == tpl.rsplit(";", 1)[0]:
            c = m.rsplit(";", 1)[1]
            if c.isdigit(): tried.add(int(c))
            if d["response"].get("error") != "E202": found.append((c, d["status"], d["response"]))
    with ThreadPoolExecutor(2) as ex: list(ex.map(one, [c for c in range(100) if c not in tried]))
    return tpl, found
with ThreadPoolExecutor(len(sys.argv) - 2) as ex:
    for tpl, f in ex.map(find, sys.argv[2:]): print(tpl, "->", f)
