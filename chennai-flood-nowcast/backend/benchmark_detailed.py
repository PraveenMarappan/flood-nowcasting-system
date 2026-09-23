"""Comprehensive post-optimization benchmark script"""
import time
import urllib.request
import gzip
import json

endpoints = [
    ("health", "http://127.0.0.1:8000/api/health"),
    ("terrain/status", "http://127.0.0.1:8000/api/terrain/status"),
    ("drainage/status", "http://127.0.0.1:8000/api/drainage/status"),
    ("locations/critical", "http://127.0.0.1:8000/api/locations/critical"),
    ("forecast?r=0", "http://127.0.0.1:8000/api/flood/forecast?rainfall=0&is_simulated=true"),
    ("forecast?r=50", "http://127.0.0.1:8000/api/flood/forecast?rainfall=50&is_simulated=true"),
    ("roads/risk?r=0 (Full)", "http://127.0.0.1:8000/api/roads/risk?forecast_offset=0&rainfall=0&is_simulated=true"),
    ("roads/risk?r=50 (Uncached)", "http://127.0.0.1:8000/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true"),
    ("roads/risk?r=50 (Cached)", "http://127.0.0.1:8000/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true"),
    ("roads/risk?r=50 (Viewport bbox)", "http://127.0.0.1:8000/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true&bbox=80.20,13.02,80.30,13.10"),
    ("drainage/diagnostics", "http://127.0.0.1:8000/api/drainage/diagnostics?latitude=13.0827&longitude=80.2707"),
    ("validation/historical (Cached)", "http://127.0.0.1:8000/api/validation/historical"),
    ("data-status", "http://127.0.0.1:8000/api/data-status"),
]

results = []
results.append(f"{'Endpoint':<35} | {'1st (ms)':>8} | {'2nd (ms)':>8} | {'3rd (ms)':>8} | {'Raw (KB)':>9} | {'Wire (KB)':>9} | Enc")
results.append("-" * 95)

for name, url in endpoints:
    times = []
    raw_size = 0
    wire_size = 0
    encoding = "none"
    for i in range(3):
        start = time.perf_counter()
        req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
        try:
            res = urllib.request.urlopen(req, timeout=30)
            wire_body = res.read()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            if i == 0:
                wire_size = len(wire_body)
                encoding = res.headers.get("Content-Encoding", "identity")
                if encoding == "gzip":
                    raw_body = gzip.decompress(wire_body)
                else:
                    raw_body = wire_body
                raw_size = len(raw_body)
        except Exception as e:
            times.append(-1)
            print(f"Error on {name}: {e}")
            
    t1 = f"{times[0]:.1f}" if times[0] >= 0 else "ERR"
    t2 = f"{times[1]:.1f}" if times[1] >= 0 else "ERR"
    t3 = f"{times[2]:.1f}" if times[2] >= 0 else "ERR"
    line = f"{name:<35} | {t1:>8} | {t2:>8} | {t3:>8} | {raw_size/1024:>9.1f} | {wire_size/1024:>9.1f} | {encoding}"
    results.append(line)

out_text = "\n".join(results)
with open("benchmark_after.txt", "w") as f:
    f.write(out_text)

print(out_text)
