from __future__ import annotations

import argparse
import re
import subprocess
import sys

SEMVER_RE = re.compile(r"^v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")


def run_git_tags() -> list[str]:
    result = subprocess.run(
        ["git", "tag", "--list", "v*.*.*"],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def parse_version(tag: str) -> tuple[int, int, int] | None:
    match = SEMVER_RE.match(tag.strip())

    if not match:
        return None

    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def latest_semver_tag(tags: list[str]) -> tuple[int, int, int] | None:
    versions = [version for tag in tags if (version := parse_version(tag)) is not None]

    if not versions:
        return None

    return sorted(versions)[-1]


def bump_version(version: tuple[int, int, int] | None, bump: str) -> tuple[int, int, int]:
    if version is None:
        return (1, 0, 0)

    major, minor, patch = version

    if bump == "major":
        return (major + 1, 0, 0)

    if bump == "minor":
        return (major, minor + 1, 0)

    if bump == "patch":
        return (major, minor, patch + 1)

    raise ValueError(f"Unsupported bump: {bump}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    parser.add_argument("--event-name", default="")
    parser.add_argument("--ref-name", default="")
    args = parser.parse_args()

    if args.event_name == "push" and SEMVER_RE.match(args.ref_name):
        print(args.ref_name)
        return 0

    next_version = bump_version(latest_semver_tag(run_git_tags()), args.bump)
    print(f"v{next_version[0]}.{next_version[1]}.{next_version[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
