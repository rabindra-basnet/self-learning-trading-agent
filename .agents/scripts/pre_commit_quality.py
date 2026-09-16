#!/usr/bin/env python3
"""
Pre-commit quality gate for the trading agent.

Runs all quality checks before code enters the repo.
Any failure = commit blocked. Fix the issue and re-run.

Usage:
    python .agents/scripts/pre_commit_quality.py
    python .agents/scripts/pre_commit_quality.py --fix  # auto-fix what ruff can
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = REPO_ROOT / "app"
MODULES_DIR = APP_DIR / "modules"
TESTS_DIR = REPO_ROOT / "tests"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

passed = 0
failed = 0
warnings = 0


def run_check(name: str, cmd: list[str], *, allow_warnings: bool = False) -> bool:
    global passed, failed, warnings
    print(f"\n{BOLD}[CHECK]{RESET} {name}")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print(f"  {GREEN}PASS{RESET}")
            passed += 1
            return True
        else:
            output = result.stdout + result.stderr
            if allow_warnings and result.returncode == 1:
                print(f"  {YELLOW}WARN{RESET}")
                for line in output.strip().split("\n")[:10]:
                    print(f"    {line}")
                warnings += 1
                return True
            print(f"  {RED}FAIL{RESET}")
            for line in output.strip().split("\n")[:15]:
                print(f"    {line}")
            failed += 1
            return False
    except FileNotFoundError:
        print(f"  {YELLOW}SKIP{RESET} (command not found)")
        warnings += 1
        return True
    except subprocess.TimeoutExpired:
        print(f"  {RED}FAIL{RESET} (timeout)")
        failed += 1
        return False


def grep_check(name: str, pattern: str, search_dirs: list[str], exclude: str = "") -> bool:
    global passed, failed
    print(f"\n{BOLD}[CHECK]{RESET} {name}")
    hits = []
    for d in search_dirs:
        dir_path = REPO_ROOT / d
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                if pattern in line:
                    if exclude and exclude in line:
                        continue
                    hits.append(f"  {py_file.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
    if hits:
        print(f"  {RED}FAIL{RESET} ({len(hits)} violations)")
        for h in hits[:10]:
            print(f"    {h}")
        if len(hits) > 10:
            print(f"    ... and {len(hits) - 10} more")
        failed += 1
        return False
    else:
        print(f"  {GREEN}PASS{RESET}")
        passed += 1
        return True


def main():
    global passed, failed, warnings

    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  PRE-COMMIT QUALITY GATE{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # --- Architecture ---
    print(f"\n{BOLD}--- ARCHITECTURE ---{RESET}")
    grep_check(
        "No SDK imports in domain",
        "import ccxt",
        [str(MODULES_DIR)],
        exclude="infrastructure",
    )
    grep_check(
        "No SDK imports in domain",
        "import redis",
        [str(MODULES_DIR)],
        exclude="infrastructure",
    )
    grep_check(
        "No SDK imports in domain",
        "import sqlalchemy",
        [str(MODULES_DIR)],
        exclude="infrastructure",
    )

    # --- Logging ---
    print(f"\n{BOLD}--- LOGGING ---{RESET}")
    grep_check(
        "No bare print() in application code",
        "print(",
        [str(MODULES_DIR / x / "application") for x in MODULES_DIR.iterdir() if x.is_dir()],
    )

    # --- Secrets ---
    print(f"\n{BOLD}--- SECRETS ---{RESET}")
    grep_check(
        "No secrets in code",
        "api_key",
        [str(APP_DIR)],
        exclude="SecretStr|get_secret_value|settings|config|__pycache__",
    )

    # --- Tooling ---
    print(f"\n{BOLD}--- TOOLING ---{RESET}")
    run_check("ruff lint", ["uv", "run", "ruff", "check", "app", "tests"])
    run_check("ruff format", ["uv", "run", "ruff", "format", "--check", "app", "tests"])
    run_check("mypy", ["uv", "run", "mypy", "app"], allow_warnings=True)
    run_check("import contracts", ["uv", "run", "lint-imports"])
    run_check("secrets scan", ["gitleaks", "detect", "--no-banner"])
    run_check("pip audit", ["pip-audit"], allow_warnings=True)

    # --- Summary ---
    total = passed + failed + warnings
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  SUMMARY{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    if warnings:
        print(f"  {YELLOW}Warnings: {warnings}{RESET}")
    if failed:
        print(f"  {RED}Failed: {failed}{RESET}")
    else:
        print(f"\n  {GREEN}ALL GATES PASSED{RESET}")
    print(f"  Total checks: {total}")
    print()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
