"""Profile backend endpoint response times - output to file"""
import time
import urllib.request

endpoints = [
    ("health", "http://localhost:8000/api/health"),
    ("terrain/status", "http://localhost:8000/api/terrain/status"),
    ("drainage/status", "http://localhost:8000/api/drainage/status"),
    ("locations/critical", "http://localhost:8000/api/locations/critical"),
    ("forecast?r=0", "http://localhost:8000/api/flood/forecast?rainfall=0&is_simulated=true"),
    ("forecast?r=50", "http://localhost:8000/api/flood/forecast?rainfall=50&is_simulated=true"),
    ("roads/risk?r=0", "http://localhost:8000/api/roads/risk?forecast_offset=0&rainfall=0&is_simulated=true"),
    ("roads/risk?r=50", "http://localhost:8000/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true"),
    ("roads/risk?r=50 repeat", "http://localhost:8000/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true"),
    ("drainage/diagnostics", "http://localhost:8000/api/drainage/diagnostics?latitude=13.0827&longitude=80.2707"),
    ("validation/historical", "http://localhost:8000/api/validation/historical"),
    ("data-status", "http://localhost:8000/api/data-status"),
]

lines = []
for name, url in endpoints:
    times = []
    size = 0
    for i in range(3):
        start = time.perf_counter()
        try:
            req = urllib.request.urlopen(url, timeout=60)
            body = req.read()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            if i == 0:
                size = len(body)
        except Exception as e:
            times.append(-1)
    
    line = f"{name}: {times[0]:.0f}ms / {times[1]:.0f}ms / {times[2]:.0f}ms | {size/1024:.1f}KB"
    lines.append(line)

with open("profile_results.txt", "w") as f:
    f.write("\n".join(lines))
    f.write("\nDONE\n")

print("Results written to profile_results.txt")
