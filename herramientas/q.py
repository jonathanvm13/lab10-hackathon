# Uso: q.py SEQ "hipotesis" '{"m":"..."}' [METODO] [RUTA] [--noauth|--token=X] [--conclusion=texto]
import sys, json, time, urllib.request, urllib.error, os
S = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.environ.get("CAJA_TOKEN_FILE", os.path.expanduser("~/.config/caja-negra/token"))
BASE = "https://caja-negra-production-c64f.up.railway.app"
LOG = os.environ.get("CAJA_LOG_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "pruebas", "experimentos.jsonl")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
flags = [a for a in sys.argv[1:] if a.startswith("--")]
seq, hip, body = args[0], args[1], args[2]
method = args[3] if len(args) > 3 else "POST"
path = args[4] if len(args) > 4 else "/msg"
token = open(TOKEN_FILE).read().strip()
for f in flags:
    if f == "--noauth": token = None
    elif f.startswith("--token="): token = f.split("=", 1)[1]
data = body.encode() if body != "-" else None
req = urllib.request.Request(BASE + path, data=data, method=method)
if data is not None: req.add_header("Content-Type", "application/json")
if token: req.add_header("Authorization", f"Bearer {token}")
time.sleep(0.12)
try:
    r = urllib.request.urlopen(req, timeout=10); status, raw, h = r.status, r.read().decode(), r.headers
except urllib.error.HTTPError as e:
    status, raw, h = e.code, e.read().decode(), e.headers
if h.get("X-Frontier-Infra"): print("RATE LIMIT"); sys.exit(1)
try: resp = json.loads(raw)
except Exception: resp = raw
try: reqj = json.loads(body)
except Exception: reqj = body
n = sum(1 for _ in open(LOG)) + 1 if os.path.exists(LOG) else 1
xr = h.get("X-Req")
own = open(TOKEN_FILE).read().strip()
conc = next((f.split("=", 1)[1] for f in flags if f.startswith("--conclusion=")), "")
if method != "POST" or path != "/msg" or token != own:
    auth = "sin token" if token is None else ("token propio" if token == own else "token ajeno")
    hip = f"[{method} {path} {auth}] {hip}"
line = {"id": n, "seq": seq, "x_req": int(xr) if xr and xr.isdigit() else xr, "hipotesis": hip,
        "request": reqj, "status": status, "response": resp, "conclusion": conc}
open(LOG, "a").write(json.dumps(line, ensure_ascii=False) + "\n")
print(n, status, xr, raw)
