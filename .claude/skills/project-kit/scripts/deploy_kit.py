#!/usr/bin/env python3
"""
Deploy a Project Kit into an existing project folder (manifest-driven, non-destructive).

Reads <kits-root>/<kit>/manifest.json and copies each `deployable` entry into
<project>/<deploy_root>/ preserving relative structure. Never overwrites an existing file
unless --force. Prints post-deploy notes and a dossier-stamp reminder.

Usage:
    # list available kits
    python3 deploy_kit.py list

    # preview a deploy
    python3 deploy_kit.py deploy --kit "Power BI Project Kit" --project "04_Portfolio/PowerBI_New_Build" --dry-run

    # do it
    python3 deploy_kit.py deploy --kit "Power BI Project Kit" --project "04_Portfolio/PowerBI_New_Build"
"""

import argparse
import json
import os
import shutil
import sys
import uuid

# vault root = four levels up: <vault>/.claude/skills/project-kit/scripts/deploy_kit.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
DEFAULT_KITS_ROOT = os.path.join(VAULT_ROOT, "06_Templates", "Kits")


def resolve(path):
    """Resolve a path as absolute, or relative to the vault root."""
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(VAULT_ROOT, path))


def is_within(path, parent):
    try:
        return (
            os.path.commonpath([os.path.realpath(path), os.path.realpath(parent)])
            == os.path.realpath(parent)
        )
    except ValueError:
        return False


def validate_project_path(project):
    root = os.path.realpath(VAULT_ROOT)
    project_real = os.path.realpath(project)
    allowed_roots = [
        os.path.join(root, "02_Clients"),
        os.path.join(root, "04_Portfolio"),
    ]
    if not any(is_within(project_real, allowed) for allowed in allowed_roots):
        return "project folder must be inside 02_Clients/ or 04_Portfolio/"
    rel_parts = os.path.relpath(project_real, root).split(os.sep)
    if any(part in {"client-comms", "contracts", "intake"} for part in rel_parts):
        return "project folder cannot be inside a confidential client subfolder"
    if "data" in rel_parts and "raw" in rel_parts:
        return "project folder cannot be inside data/raw"
    return ""


def list_kits(kits_root):
    if not os.path.isdir(kits_root):
        print("No kits root at {}".format(kits_root))
        return 1
    found = False
    for name in sorted(os.listdir(kits_root)):
        manifest = os.path.join(kits_root, name, "manifest.json")
        if os.path.isfile(manifest):
            found = True
            with open(manifest) as f:
                m = json.load(f)
            print("- {}  (v{})  {}".format(
                m.get("kit", name), m.get("version", "?"), m.get("one_liner", "")))
    if not found:
        print("No kits with a manifest.json found in {}".format(kits_root))
    return 0


def copy_entry(src, dest, kind, dry_run, force, log):
    if kind == "dir":
        if not os.path.isdir(src):
            log.append(("MISSING", src))
            return
        for root, _dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            for fn in files:
                s = os.path.join(root, fn)
                d = os.path.join(dest, rel, fn) if rel != "." else os.path.join(dest, fn)
                _copy_file(s, d, dry_run, force, log)
    else:
        if not os.path.isfile(src):
            log.append(("MISSING", src))
            return
        _copy_file(src, dest, dry_run, force, log)


def _stamp_fresh_id(dest):
    """Give a freshly-deployed Markdown file its own UUID so template ids never collide across
    instances (the template carries an id; each deployed instance gets a new one)."""
    if not dest.endswith(".md"):
        return
    try:
        with open(dest, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
    except (IOError, OSError, UnicodeDecodeError):
        return
    if not lines or lines[0].strip() != "---":
        return
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return
    new_id = str(uuid.uuid4())
    id_idx = next((i for i in range(1, end) if lines[i].startswith("id:")), None)
    if id_idx is not None:
        lines[id_idx] = "id: " + new_id
    else:
        lines.insert(1, "id: " + new_id)
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _copy_file(s, d, dry_run, force, log):
    if os.path.exists(d) and not force:
        log.append(("SKIP (exists)", d))
        return
    if dry_run:
        log.append(("WOULD COPY", d))
        return
    dparent = os.path.dirname(d)
    if dparent:
        os.makedirs(dparent, exist_ok=True)
    shutil.copy2(s, d)
    _stamp_fresh_id(d)
    log.append(("COPIED", d))


def deploy(args):
    kits_root = resolve(args.kits_root) if args.kits_root else DEFAULT_KITS_ROOT
    kit_dir = os.path.join(kits_root, args.kit)
    manifest_path = os.path.join(kit_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        print("ERROR: no manifest at {}".format(manifest_path))
        return 2
    with open(manifest_path) as f:
        m = json.load(f)

    project = resolve(args.project)
    validation_error = validate_project_path(project)
    if validation_error:
        print("ERROR: {}".format(validation_error))
        return 2
    if not os.path.isdir(project):
        print("ERROR: project folder not found: {}".format(project))
        return 2

    deploy_root = args.dest_name or m.get("deploy_root", "Kit")
    dest_base = os.path.join(project, deploy_root)

    print("Kit:       {} (v{})".format(m.get("kit"), m.get("version")))
    print("From:      {}".format(kit_dir))
    print("Into:      {}".format(dest_base))
    print("Mode:      {}{}".format("DRY-RUN " if args.dry_run else "LIVE",
                                   "(force overwrite)" if args.force else ""))
    print("-" * 60)

    log = []
    for entry in m.get("deployable", []):
        src = os.path.join(kit_dir, entry["path"])
        dest = os.path.join(dest_base, entry["path"])
        copy_entry(src, dest, entry.get("kind", "file"), args.dry_run, args.force, log)

    for status, path in log:
        rel = os.path.relpath(path, project)
        display_path = rel if not rel.startswith("..") and not os.path.isabs(rel) else path
        print("  {:<16} {}".format(status, display_path))

    copied = sum(1 for s, _ in log if s in ("COPIED", "WOULD COPY"))
    skipped = sum(1 for s, _ in log if s.startswith("SKIP"))
    missing = sum(1 for s, _ in log if s == "MISSING")
    print("-" * 60)
    print("{} file(s) {}, {} skipped, {} missing.".format(
        copied, "to copy" if args.dry_run else "copied", skipped, missing))

    notes = m.get("post_deploy_notes", [])
    if notes:
        print("\nPost-deploy notes:")
        for n in notes:
            print("  - {}".format(n))
    print("\nNext: stamp the deployed path into the project dossier and log the session (CLAUDE write protocol).")
    return 3 if missing else 0


def main():
    p = argparse.ArgumentParser(description="Deploy a Project Kit into a project folder.")
    sub = p.add_subparsers(dest="cmd")

    pl = sub.add_parser("list", help="List available kits.")
    pl.add_argument("--kits-root", default=None)

    pd = sub.add_parser("deploy", help="Deploy a kit into a project.")
    pd.add_argument("--kit", required=True, help='Kit name, e.g. "Power BI Project Kit".')
    pd.add_argument("--project", required=True, help="Project folder (abs, or relative to vault root).")
    pd.add_argument("--kits-root", default=None)
    pd.add_argument("--dest-name", default=None, help="Destination subfolder name (default: manifest deploy_root).")
    pd.add_argument("--dry-run", action="store_true")
    pd.add_argument("--force", action="store_true", help="Overwrite existing files.")

    args = p.parse_args()
    if args.cmd == "list":
        return list_kits(resolve(args.kits_root) if args.kits_root else DEFAULT_KITS_ROOT)
    if args.cmd == "deploy":
        return deploy(args)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
