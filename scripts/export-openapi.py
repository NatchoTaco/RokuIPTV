from __future__ import annotations

import json
from pathlib import Path

from streamforge_api.main import create_app


def main() -> None:
    app = create_app()
    output_path = Path("packages/api-contract/openapi.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
