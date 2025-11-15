#!/usr/bin/env python3
"""Helper script to create Alembic revisions with timestamp-based naming."""
import subprocess
import sys


def main():
    """Create a new Alembic revision with timestamp-based naming."""
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/alembic_revision.py <message> [--autogenerate]")
        sys.exit(1)

    message = sys.argv[1]
    autogenerate = "--autogenerate" in sys.argv or "-a" in sys.argv

    cmd = ["uv", "run", "alembic", "revision", "-m", message]
    if autogenerate:
        cmd.append("--autogenerate")

    print(f"Creating migration: {message}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
