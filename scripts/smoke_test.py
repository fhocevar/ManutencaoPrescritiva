import json
from pathlib import Path

import httpx

API = "http://localhost:8000"


def main() -> None:
    print(httpx.get(f"{API}/health/ready", timeout=10).json())
    payload = json.loads(Path("data/sample_event.json").read_text(encoding="utf-8"))
    response = httpx.post(f"{API}/api/v1/events/analyze", json=payload, timeout=60)
    print(response.status_code)
    print(response.text[:1000])


if __name__ == "__main__":
    main()
