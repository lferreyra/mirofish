#!/usr/bin/env python3
"""
Build a source bundle from normalized Federal Register/BIS policy-feed input.
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module():
    services_root = Path(__file__).resolve().parents[1] / "backend" / "app" / "services"

    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = []
    services_pkg = types.ModuleType("app.services")
    services_pkg.__path__ = [str(services_root)]
    sys.modules["app"] = app_pkg
    sys.modules["app.services"] = services_pkg

    full_name = "app.services.policy_feed_connector"
    if full_name not in sys.modules:
        spec = spec_from_file_location(full_name, services_root / "policy_feed_connector.py")
        module = module_from_spec(spec)
        sys.modules[full_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    return sys.modules[full_name]


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy_feed_json", type=Path)
    parser.add_argument("--existing-source-bundle", type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    module = _load_module()
    existing = _load_json(args.existing_source_bundle) if args.existing_source_bundle else None
    payload = module.build_policy_feed_source_bundle(
        _load_json(args.policy_feed_json),
        existing_source_bundle=existing,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

