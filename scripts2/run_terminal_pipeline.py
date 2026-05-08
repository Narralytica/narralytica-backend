from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts2"


def _run_step(name: str, args: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "name": name,
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build terminal payloads and optionally publish them to Supabase.")
    parser.add_argument("--skip-brief", action="store_true", help="Do not run the xAI desk brief step.")
    parser.add_argument("--force-brief", action="store_true", help="Regenerate the xAI desk brief even if today's brief exists.")
    parser.add_argument("--publish", action="store_true", help="Publish payloads to the Supabase terminal_payloads table after building.")
    parser.add_argument("--dry-run-publish", action="store_true", help="Validate the Supabase publish plan without writing.")
    args = parser.parse_args()

    steps: list[dict[str, object]] = []
    steps.append(_run_step("build_website_data", [str(SCRIPTS_DIR / "build_website_data.py")]))

    if steps[-1]["ok"] and not args.skip_brief:
        brief_args = [str(SCRIPTS_DIR / "generate_desk_brief.py")]
        if args.force_brief:
            brief_args.append("--force")
        steps.append(_run_step("generate_desk_brief", brief_args))

    if steps[-1]["ok"] and (args.publish or args.dry_run_publish):
        publish_args = [str(SCRIPTS_DIR / "publish_terminal_payloads.py")]
        if args.dry_run_publish:
            publish_args.append("--dry-run")
        steps.append(_run_step("publish_terminal_payloads", publish_args))

    ok = all(bool(step["ok"]) for step in steps)
    print(json.dumps({"ok": ok, "steps": steps}, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
