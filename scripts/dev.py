#!/usr/bin/env python3
"""Development scripts for the Python server project."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list[str], description: str) -> int:
    """Run a command and return its exit code."""
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def lint() -> int:
    """Run all linting tools."""
    print("🔍 Running linting tools...")

    commands = [
        (["ruff", "check", "."], "Ruff linting"),
        (["black", "--check", "."], "Black formatting check"),
        (["isort", "--check-only", "."], "Import sorting check"),
        (["mypy", "app"], "Type checking"),
    ]

    for cmd, desc in commands:
        if run_command(cmd, desc) != 0:
            return 1

    print("✅ All linting checks passed!")
    return 0


def format_code() -> int:
    """Format code with black and isort."""
    print("🎨 Formatting code...")

    commands = [
        (["black", "."], "Black formatting"),
        (["isort", "."], "Import sorting"),
        (["ruff", "check", "--fix", "."], "Ruff auto-fixes"),
    ]

    for cmd, desc in commands:
        if run_command(cmd, desc) != 0:
            return 1

    print("✅ Code formatting complete!")
    return 0


def test() -> int:
    """Run tests."""
    print("🧪 Running tests...")
    return run_command(
        ["pytest", "-v", "--cov=app", "--cov-report=term-missing"],
        "Running pytest with coverage",
    )


def dev_server() -> int:
    """Start the development server."""
    print("🚀 Starting development server...")
    return run_command(
        [
            "python",
            "-m",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        "Starting uvicorn development server",
    )


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/dev.py <command>")
        print("Commands: lint, format, test, serve")
        sys.exit(1)

    command = sys.argv[1]

    if command == "lint":
        sys.exit(lint())
    elif command == "format":
        sys.exit(format_code())
    elif command == "test":
        sys.exit(test())
    elif command == "serve":
        sys.exit(dev_server())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
