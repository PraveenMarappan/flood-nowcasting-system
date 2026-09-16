import urllib.request
import json
import time

urls = [
    '/api/health',
    '/api/terrain/status',
    '/api/terrain/elevation?latitude=13.0827&longitude=80.2707',
    '/api/terrain/elevation?latitude=13.10&longitude=80.25',
    '/api/terrain/elevation?latitude=12.5&longitude=80.25',
    '/api/rainfall/current',
    '/api/data-status',
    '/api/flood/current',
    '/api/flood/forecast',
    '/api/drainage/status'
]

with open("test_output.txt", "w") as f:
    for p in urls:
        f.write(f'\n--- {p} ---\n')
        try:
            req = urllib.request.Request('http://127.0.0.1:8000' + p)
            with urllib.request.urlopen(req) as response:
                f.write(json.dumps(json.loads(response.read().decode()), indent=2) + "\n")
        except urllib.error.HTTPError as e:
            f.write(f'HTTPError: {e.code}\n')
        except Exception as e:
            f.write(f'Error: {e}\n')
