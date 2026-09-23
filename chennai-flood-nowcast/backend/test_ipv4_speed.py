"""Test IPv4 vs localhost resolution speed"""
import time
import urllib.request

def test_url(url):
    start = time.perf_counter()
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    try:
        res = urllib.request.urlopen(req)
        content = res.read()
        elapsed = (time.perf_counter() - start) * 1000
        headers = dict(res.headers)
        return elapsed, len(content), headers.get("Content-Encoding")
    except Exception as e:
        return -1, 0, str(e)

print("Testing localhost...")
t_lh, s_lh, enc_lh = test_url("http://localhost:8000/api/health")
print(f"http://localhost:8000/api/health -> {t_lh:.1f} ms")

print("Testing 127.0.0.1...")
t_ip, s_ip, enc_ip = test_url("http://127.0.0.1:8000/api/health")
print(f"http://127.0.0.1:8000/api/health -> {t_ip:.1f} ms")

print("Testing 127.0.0.1 roads/risk with gzip...")
t_rd, s_rd, enc_rd = test_url("http://127.0.0.1:8000/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true")
print(f"http://127.0.0.1:8000/api/roads/risk -> {t_rd:.1f} ms, compressed size: {s_rd/1024:.1f} KB, encoding: {enc_rd}")

print("Testing 127.0.0.1 roads/risk CACHED call...")
t_rd2, s_rd2, enc_rd2 = test_url("http://127.0.0.1:8000/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true")
print(f"http://127.0.0.1:8000/api/roads/risk CACHED -> {t_rd2:.1f} ms, compressed size: {s_rd2/1024:.1f} KB")

print("Testing 127.0.0.1 roads/risk WITH BBOX...")
t_bbox, s_bbox, enc_bbox = test_url("http://127.0.0.1:8000/api/roads/risk?forecast_offset=0&rainfall=50&is_simulated=true&bbox=80.20,13.02,80.30,13.10")
print(f"http://127.0.0.1:8000/api/roads/risk WITH BBOX -> {t_bbox:.1f} ms, compressed size: {s_bbox/1024:.1f} KB")
