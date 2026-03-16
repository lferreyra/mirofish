#!/usr/bin/env python3
"""
Generate a structural parse JSON artifact from a curated source bundle.
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_parser_module():
    services_root = Path(__file__).resolve().parents[1] / "backend" / "app" / "services"

    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = []
    services_pkg = types.ModuleType("app.services")
    services_pkg.__path__ = [str(services_root)]
    sys.modules["app"] = app_pkg
    sys.modules["app.services"] = services_pkg

    for name in ["research_ontology", "structural_parser"]:
        full_name = f"app.services.{name}"
        if full_name in sys.modules:
            continue
        spec = spec_from_file_location(full_name, services_root / f"{name}.py")
        module = module_from_spec(spec)
        sys.modules[full_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    return sys.modules["app.services.structural_parser"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to source bundle JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Where to write structural parse JSON. Defaults to stdout.",
    )
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    module = _load_parser_module()
    output = module.build_structural_parse_from_source_bundle(payload)
    rendered = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
