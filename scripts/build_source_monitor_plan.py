#!/usr/bin/env python3
"""
Build a source monitoring manifest from a source acquisition plan.
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_source_registry_module():
    services_root = Path(__file__).resolve().parents[1] / "backend" / "app" / "services"

    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = []
    services_pkg = types.ModuleType("app.services")
    services_pkg.__path__ = [str(services_root)]
    sys.modules["app"] = app_pkg
    sys.modules["app.services"] = services_pkg

    full_name = "app.services.source_registry"
    if full_name not in sys.modules:
        spec = spec_from_file_location(full_name, services_root / "source_registry.py")
        module = module_from_spec(spec)
        sys.modules[full_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    return sys.modules[full_name]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_acquisition_plan_json", type=Path)
    parser.add_argument("--max-tasks", type=int, default=20)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    module = _load_source_registry_module()
    acquisition_plan = json.loads(args.source_acquisition_plan_json.read_text(encoding="utf-8"))
    monitor_plan = module.build_source_monitor_plan(
        acquisition_plan,
        max_tasks=args.max_tasks,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(monitor_plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
