#!/usr/bin/env python3
"""Fail when the coverage of any file is below the limit.

``fail_under`` in ``pyproject.toml`` checks the total only. Run it after
``pytest``, it reads ``.coverage``.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

LIMIT = 95.0  # percent, the same as `fail_under`; the ideal is 100


def main() -> int:
    """Return 1 if some file has the coverage below the limit."""
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "coverage.json"
        # the command is fixed, it has no input from outside
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "coverage", "json", "--quiet",
             "--fail-under=0",
             "-o", str(output)],
            check=True)
        files = json.loads(output.read_text(encoding="utf-8"))["files"]

    failed = {
        name: data["summary"]["percent_covered"]
        for name, data in files.items()
        if data["summary"]["percent_covered"] < LIMIT
    }
    for name, percent in sorted(failed.items()):
        print(f"{name}: {percent:.1f} % is below {LIMIT:.0f} %")  # noqa: T201
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
