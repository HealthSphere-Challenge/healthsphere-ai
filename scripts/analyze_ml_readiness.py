#!/usr/bin/env python3
"""Generate the deterministic Stage 8 readiness evidence as JSON."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthsphere_ai.cohort import audit_all  # noqa: E402

source = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/synthea_5000_reproducible/csv")
print(json.dumps(audit_all(source), indent=2, sort_keys=True))
