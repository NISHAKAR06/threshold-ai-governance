import requests

urls = [
 'https://threshold-ai-governance.onrender.com/api/v1/dashboard/stats',
 'https://threshold-ai-governance.onrender.com/api/v1/review?limit=10',
 'https://threshold-ai-governance.onrender.com/api/v1/audit?limit=10',
 'https://threshold-ai-governance.onrender.com/api/v1/settings',
]
for u in urls:
    try:
        r = requests.get(u, timeout=15)
        print(u, r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text[:200])
    except Exception as e:
        print(u, 'ERROR', e)
