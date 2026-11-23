"""Run the internal Coforge resume batch from a project checkout."""

import os
from pathlib import Path

_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))

from resume_automation.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
