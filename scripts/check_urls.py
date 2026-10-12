#!/usr/bin/env python3
"""Verify the URLs in data/directories.csv (or a urls.tsv with key<TAB>kind<TAB>url rows).

Outputs check_results.json next to this script. Usage: python3 check_urls.py
"""
import json, os, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
tasks = []
tsv = os.path.join(HERE, "urls.tsv")
if os.path.exists(tsv):
    with open(tsv) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3:
                tasks.append(tuple(parts))

results_path = os.path.join(HERE, "check_results.json")
done = {}
if os.path.exists(results_path):
    try:
        done = json.load(open(results_path))
    except Exception:
        done = {}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

def check(t):
    key, kind, url = t
    tid = key + "|" + kind
    if tid in done:
        return None
    try:
        r = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-L", "--max-time", "20",
             "--connect-timeout", "8", "-A", UA,
             "-w", "%{http_code}\t%{url_effective}\t%{num_redirects}", url],
            capture_output=True, text=True, timeout=35)
        out = r.stdout.strip().split("\t")
        code = out[0] if out and out[0] else "000"
        final = out[1] if len(out) > 1 else ""
        err = (r.stderr or "").strip().replace("\n", " ")[:200]
    except Exception as e:
        code, final, err = "000", "", str(e)[:200]
    return (tid, dict(code=code, final=final, err=err))

with ThreadPoolExecutor(max_workers=24) as ex:
    for fu in as_completed([ex.submit(check, t) for t in tasks]):
        res = fu.result()
        if res:
            done[res[0]] = res[1]
            if len(done) % 100 == 0:
                json.dump(done, open(results_path, "w"), indent=0)
                print(len(done), "checked", flush=True)

json.dump(done, open(results_path, "w"), indent=1)
print("TOTAL:", len(done), "of", len(tasks))
