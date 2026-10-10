#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seq de humo para la caja negra (reto de ingenieria inversa autorizado).

Uso:
  python3 -I herramientas/humo.py --grabar   # graba la linea base en herramientas/humo-base.json
  python3 -I herramientas/humo.py            # compara contra la linea base

Solo biblioteca estandar, Python 3.6+. El token nunca se imprime ni se escribe en ningun archivo.
"""
import sys
import os
import json
import time
import urllib.request
import urllib.error

BASE_URL = "https://caja-negra-production-c64f.up.railway.app"
HERE = os.path.dirname(os.path.abspath(__file__))
CASES_PATH = os.path.join(HERE, "humo.jsonl")
BASE_PATH = os.path.join(HERE, "humo-base.json")
LOG_PATH = os.environ.get("CAJA_LOG_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "pruebas", "experimentos.jsonl")
DEFAULT_TOKEN_FILE = os.path.expanduser("~/.config/caja-negra/token")
INVALID_TOKEN = "token-invalido-para-pruebas-0000"
MIN_INTERVAL = 0.21          # <= 5 req/s
RATE_WAIT = 2.0              # espera ante rate-limit
AUTH_WORDS = {"propio": "token propio", "sin": "sin token", "invalido": "token inválido"}

_last_req = [0.0]


def read_token():
    path = os.environ.get("CAJA_TOKEN_FILE", DEFAULT_TOKEN_FILE)
    with open(path, "r") as f:
        return f.read().strip()


def throttle():
    dt = time.time() - _last_req[0]
    if dt < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - dt)
    _last_req[0] = time.time()


def do_request(method, path, auth, body, token):
    """Envia un request con reintento ante rate-limit. Devuelve (status, raw_text, x_req)."""
    while True:
        throttle()
        url = BASE_URL + path
        data = None
        headers = {}
        if body is not None:
            if isinstance(body, str):
                data = body.encode("utf-8")
            else:
                data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth == "propio":
            headers["Authorization"] = "Bearer " + token
        elif auth == "invalido":
            headers["Authorization"] = "Bearer " + INVALID_TOKEN
        # auth == "sin": sin cabecera Authorization
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            status = resp.getcode()
            raw = resp.read().decode("utf-8", "replace")
            hdrs = resp.headers
        except urllib.error.HTTPError as e:
            status = e.code
            raw = e.read().decode("utf-8", "replace")
            hdrs = e.headers
        infra = hdrs.get("X-Frontier-Infra")
        if infra and infra.strip().lower() == "rate-limit":
            time.sleep(RATE_WAIT)
            continue  # no se registra: reintentar
        xreq_raw = hdrs.get("X-Req")
        try:
            xreq = int(xreq_raw) if xreq_raw is not None else None
        except (ValueError, TypeError):
            xreq = None
        return status, raw, xreq


def parse_body(raw):
    try:
        return json.loads(raw), True
    except Exception:
        return raw, False


def body_str(raw):
    obj, is_json = parse_body(raw)
    if is_json:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return raw


def summary(status, raw):
    return "%s %s" % (status, body_str(raw))


def bodies_equal(raw_a, raw_b):
    a, aj = parse_body(raw_a)
    b, bj = parse_body(raw_b)
    if aj and bj:
        return a == b
    return raw_a == raw_b


def request_field(body):
    if body is None:
        return "-"
    return body  # string crudo o objeto


def build_hip(case):
    method, path, auth = case["method"], case["path"], case["auth"]
    core = case["hipotesis"]
    if method == "POST" and path == "/__reset" and auth == "propio":
        return "[POST /__reset] reset: inicia la seq %s con estado limpio" % case["seq"]
    if method == "POST" and path == "/msg" and auth == "propio":
        return core
    return "[%s %s %s] %s" % (method, path, AUTH_WORDS[auth], core)


def count_log_lines(path):
    if not os.path.exists(path):
        return 0
    n = 0
    with open(path, "rb") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def ensure_trailing_newline(path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            f.seek(-1, os.SEEK_END)
            last = f.read(1)
        if last != b"\n":
            with open(path, "ab") as f:
                f.write(b"\n")


def main():
    grabar = "--grabar" in sys.argv[1:]
    token = read_token()

    with open(CASES_PATH, encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    baseline = None
    if not grabar:
        with open(BASE_PATH, encoding="utf-8") as f:
            baseline = json.load(f)

    hhmm = time.strftime("%H%M")
    ensure_trailing_newline(LOG_PATH)
    next_id = count_log_lines(LOG_PATH) + 1

    new_baseline = {}
    changes = []
    first_id = None
    last_id = None

    with open(LOG_PATH, "a", encoding="utf-8") as logf:
        for i, case in enumerate(cases):
            status, raw, xreq = do_request(
                case["method"], case["path"], case["auth"], case["body"], token)
            key = str(i)
            hip = build_hip(case)

            if grabar:
                concl = "línea base: " + summary(status, raw)
                new_baseline[key] = {"status": status, "raw": raw, "seq": case["seq"]}
            else:
                b = baseline[key]
                same = (b["status"] == status) and bodies_equal(b["raw"], raw)
                if same:
                    concl = "igual a la línea base"
                else:
                    before = summary(b["status"], b["raw"])
                    after = summary(status, raw)
                    concl = "CAMBIO: antes %s → ahora %s" % (before, after)
                    changes.append(("humo-%s-%s" % (hhmm, case["seq"]), hip, before, after))

            entry = {
                "id": next_id,
                "seq": "humo-%s-%s" % (hhmm, case["seq"]),
                "x_req": xreq,
                "hipotesis": hip,
                "request": request_field(case["body"]),
                "status": status,
                "response": parse_body(raw)[0],
                "conclusion": concl,
            }
            logf.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logf.flush()
            if first_id is None:
                first_id = next_id
            last_id = next_id
            next_id += 1

    if grabar:
        with open(BASE_PATH, "w", encoding="utf-8") as f:
            json.dump(new_baseline, f, ensure_ascii=False, indent=2)
        print("línea base grabada: %d casos (ids %s-%s en %s)"
              % (len(cases), first_id, last_id, LOG_PATH))
        return 0

    for seq, hip, before, after in changes:
        print("%s | %s | %s → %s" % (seq, hip, before, after))
    print("%d casos, %d cambios (ids %s-%s)" % (len(cases), len(changes), first_id, last_id))
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
