#!/usr/bin/env python3
"""Check the target graph of a Swift package against declared layers.

Reads the layer rules from a JSON file (see references/project-structure.md):

    {
      "layers": [
        {"name": "app", "modules": ["AppFeature"]},
        {"name": "features", "modules": ["Settings", "Search"], "isolated": true},
        {"name": "shared", "modules": ["DesignSystem", "*Client", "*Interface"]}
      ],
      "allow": [["Search", "Settings"]]
    }

Layers are listed from top to bottom. A module may depend on modules of lower
layers and, unless its layer is "isolated", on modules of its own layer. Module
names may use shell-style wildcards. "allow" lists documented exceptions as
[from, to] pairs. Test targets are skipped; every other target must belong to a
layer, so new modules get classified when they are added.

Exit codes: 0 = graph follows the rules, 1 = violations, 2 = usage or input error.
"""

import argparse
import fnmatch
import json
import subprocess
import sys


def load_describe(args):
    if args.describe_json:
        with open(args.describe_json, encoding="utf-8") as handle:
            return json.load(handle)
    result = subprocess.run(
        ["swift", "package", "describe", "--type", "json"],
        cwd=args.package_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.exit(f"error: swift package describe failed:\n{result.stderr.strip()}")
    return json.loads(result.stdout)


def layer_index(module, layers):
    for index, layer in enumerate(layers):
        if any(fnmatch.fnmatchcase(module, pattern) for pattern in layer["modules"]):
            return index
    return None


def check(describe, rules):
    layers = rules["layers"]
    allowed = {tuple(pair) for pair in rules.get("allow", [])}
    targets = [t for t in describe.get("targets", []) if t.get("type") != "test"]
    problems = []
    for target in targets:
        name = target["name"]
        own = layer_index(name, layers)
        if own is None:
            problems.append(f"{name}: not assigned to any layer")
            continue
        for dependency in target.get("target_dependencies") or []:
            if (name, dependency) in allowed:
                continue
            other = layer_index(dependency, layers)
            if other is None:
                problems.append(f"{name} -> {dependency}: dependency not assigned to any layer")
            elif other < own:
                problems.append(
                    f"{name} -> {dependency}: {layers[own]['name']} must not depend on "
                    f"the higher layer {layers[other]['name']}"
                )
            elif other == own and layers[own].get("isolated", False):
                problems.append(
                    f"{name} -> {dependency}: modules of {layers[own]['name']} must not "
                    "depend on each other"
                )
    return len(targets), problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rules", help="JSON file with the layer rules")
    parser.add_argument("--package-path", default=".", help="package directory (default: .)")
    parser.add_argument(
        "--describe-json", help="use saved `swift package describe --type json` output"
    )
    args = parser.parse_args()
    try:
        with open(args.rules, encoding="utf-8") as handle:
            rules = json.load(handle)
        describe = load_describe(args)
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    count, problems = check(describe, rules)
    for problem in problems:
        print(f"violation: {problem}")
    print(f"{count} modules checked, {len(problems)} violation(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
