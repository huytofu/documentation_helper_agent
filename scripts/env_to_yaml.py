"""Convert .env to Cloud Run --env-vars-file JSON object format."""
import json
import sys
from pathlib import Path


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else ".env")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "env.yaml")

    env: dict[str, str] = {}
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value

    dst.write_text(json.dumps(env, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(env)} variables to {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
