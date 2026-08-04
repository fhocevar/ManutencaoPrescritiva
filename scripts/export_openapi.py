import argparse
import json
from pathlib import Path

from app.presentation.api.main import app


def main(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OpenAPI exportado para {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/openapi.json"))
    args = parser.parse_args()
    main(args.output)
