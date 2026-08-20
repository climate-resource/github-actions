#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = ["packaging>=24.0"]
# ///
"""Bump a project's version, update the CHANGELOG, commit, tag and push.

Run by the `bump-version` composite action. Every setting arrives as an
environment variable mapped from an action input, so `action.yml` stays a
declaration of the interface and this file holds the behaviour.

The work happens in two phases:

1. `tag_release` bumps the version, mirrors it onto workspace packages, builds
   the changelog, commits and tags it, and pushes.
2. `land_prerelease` optionally lands a second commit moving the branch onto a
   pre-release version, so later commits do not share the tagged version.

Everything that differs between project types lives behind `Backend`; the two
phases themselves never branch on the project type.
"""

import os
import shlex
import subprocess
import sys
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol, Self

from packaging.version import InvalidVersion, Version

# Sentinel accepted by pre-release-base and pre-release-bump to skip that part
# of the second commit.
NONE = "none"


class BumpError(Exception):
    """A failure that should end the action with a readable message."""


# --------------------------------------------------------------------------
# Process plumbing
# --------------------------------------------------------------------------


def log(message: str) -> None:
    print(message, flush=True)


@contextmanager
def group(title: str) -> Generator[None]:
    """Fold a phase of the run into a collapsible section of the Actions log."""
    log(f"::group::{title}")
    try:
        yield
    finally:
        log("::endgroup::")


def run(command: Sequence[str], *, capture: bool = False) -> str:
    """Run `command`, echoing it first so the log shows what was executed.

    With `capture`, stdout is returned instead of being written to the log;
    stderr always flows straight through so failures stay visible.
    """
    log(f"+ {shlex.join(command)}")
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError as error:
        raise BumpError(f"command not found: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        if error.stdout:
            log(error.stdout)
        raise BumpError(
            f"command failed with exit code {error.returncode}: {shlex.join(command)}"
        ) from error
    return (result.stdout or "").strip()


def write_output(name: str, value: str) -> None:
    """Publish a step output for downstream steps to consume."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        # Running outside Actions (e.g. a local dry run); just show the value.
        log(f"[output] {name}={value}")
        return
    with open(output_file, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


# --------------------------------------------------------------------------
# Project-type backends
# --------------------------------------------------------------------------


class Backend(Protocol):
    """The project-type-specific half of a bump.

    The `*_command` methods build argument lists without running anything,
    which keeps the argument assembly (where the fiddly cases live) directly
    testable.
    """

    name: str

    def read_version(self) -> str:
        """Return the project's current version."""

    def bump_command(self, segments: Sequence[str]) -> list[str]:
        """Build the command applying `bump-rule` segments to the root project."""

    def prerelease_command(self, base: str, bump: str) -> list[str]:
        """Build the command applying the post-tag pre-release bump."""

    def workspace_command(self, package: str, version: str) -> list[str]:
        """Build the command pinning a workspace package to `version`."""

    def lock_command(self) -> list[str]:
        """Build the command refreshing the lockfile."""

    def changelog_command(self, version: str) -> list[str]:
        """Build the towncrier command assembling the CHANGELOG."""

    def is_prerelease(self, version: str) -> bool:
        """Return whether `version` is a pre-release."""

    def prerelease_label(self, requested: str, version: str) -> str:
        """Return the scope for the second commit's `bump(...)` message.

        `requested` is the raw `pre-release-bump` input and `version` the
        pre-release it produced, so a backend can use whichever reads better.
        """


class UvBackend:
    """Python projects whose version lives in `pyproject.toml`, managed by uv."""

    name = "uv"

    def read_version(self) -> str:
        return run(["uv", "version", "--short"], capture=True)

    def bump_command(self, segments: Sequence[str]) -> list[str]:
        command = ["uv", "version", "--frozen"]
        for segment in segments:
            command += ["--bump", segment]
        return command

    def prerelease_command(self, base: str, bump: str) -> list[str]:
        # Each of base and bump is a single uv bump segment, never a word list.
        segments = [] if base == NONE else [base]
        segments.append(bump)
        return self.bump_command(segments)

    def workspace_command(self, package: str, version: str) -> list[str]:
        return ["uv", "version", "--frozen", "--package", package, version]

    def lock_command(self) -> list[str]:
        return ["uv", "lock"]

    def changelog_command(self, version: str) -> list[str]:
        return ["uv", "run", "towncrier", "build", "--yes", "--version", f"v{version}"]

    def is_prerelease(self, version: str) -> bool:
        try:
            # Covers alpha, beta, rc and dev releases in one check.
            return Version(version).is_prerelease
        except InvalidVersion as error:
            raise BumpError(f"'{version}' is not a valid PEP 440 version") from error

    def prerelease_label(self, requested: str, version: str) -> str:
        # The input is already a single readable word: dev, alpha, beta, rc.
        return requested


class YarnBackend:
    """Node projects whose version lives in `package.json`.

    `npm version` is used purely as a version-bumping CLI; yarn stays the
    package manager.
    """

    name = "yarn"

    def read_version(self) -> str:
        return run(["node", "-p", "require('./package.json').version"], capture=True)

    def bump_command(self, segments: Sequence[str]) -> list[str]:
        return ["npm", "version", *segments, "--no-git-tag-version"]

    def prerelease_command(self, base: str, bump: str) -> list[str]:
        # Both values are verbatim `npm version` arguments, so they are split
        # into words and concatenated into a single call.
        segments = [] if base == NONE else base.split()
        segments += bump.split()
        return self.bump_command(segments)

    def workspace_command(self, package: str, version: str) -> list[str]:
        return ["npm", "version", "--no-git-tag-version", "--prefix", package, version]

    def lock_command(self) -> list[str]:
        return ["yarn", "install", "--mode=update-lockfile"]

    def changelog_command(self, version: str) -> list[str]:
        # No project virtualenv to run towncrier from, so fetch it on the fly.
        return ["uvx", "towncrier", "build", "--yes", "--version", f"v{version}"]

    def is_prerelease(self, version: str) -> bool:
        # In semver the pre-release is the `-...` part, which build metadata
        # (`+...`) may itself contain, so drop the metadata before looking.
        return "-" in version.split("+", 1)[0]

    def prerelease_label(self, requested: str, version: str) -> str:
        # The input is a list of npm arguments, so `bump(--preid dev)` would be
        # a poor commit scope. Read the identifier back off the version npm
        # produced instead: 1.2.5-dev.0 -> dev.
        _, _, prerelease = version.split("+", 1)[0].partition("-")
        for identifier in prerelease.split("."):
            if identifier and not identifier.isdigit():
                return identifier
        # npm was asked for a bare `prerelease` with no --preid, giving a
        # numeric-only identifier such as 1.2.4-0.
        return "prerelease"


BACKENDS: dict[str, type[Backend]] = {"uv": UvBackend, "yarn": YarnBackend}


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


def as_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def as_lines(value: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in value.splitlines() if line.strip())


@dataclass(frozen=True)
class Config:
    project_type: str
    bump_rule: str
    pre_release_bump: str
    pre_release_base: str
    update_changelog: bool
    workspace_packages: tuple[str, ...]
    run_lock: bool
    pre_commit_command: str
    commit_skip_hooks: bool
    do_push: bool

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Self:
        source = os.environ if env is None else env

        def get(name: str, default: str = "") -> str:
            return source.get(name, default)

        return cls(
            project_type=get("PROJECT_TYPE", "uv").strip(),
            bump_rule=get("BUMP_RULE"),
            pre_release_bump=get("PRE_RELEASE_BUMP", "dev").strip(),
            pre_release_base=get("PRE_RELEASE_BASE", "patch").strip(),
            update_changelog=as_bool(get("UPDATE_CHANGELOG", "true")),
            workspace_packages=as_lines(get("WORKSPACE_PACKAGES")),
            run_lock=as_bool(get("RUN_LOCK", "true")),
            pre_commit_command=get("PRE_COMMIT_COMMAND").strip(),
            commit_skip_hooks=as_bool(get("COMMIT_SKIP_HOOKS", "false")),
            do_push=as_bool(get("DO_PUSH", "true")),
        )

    @property
    def bump_segments(self) -> list[str]:
        return self.bump_rule.split()

    def backend(self) -> Backend:
        if self.project_type not in BACKENDS:
            raise BumpError(
                f"project-type must be one of {', '.join(sorted(BACKENDS))}, "
                f"got '{self.project_type}'"
            )
        if not self.bump_segments:
            raise BumpError("bump-rule must not be empty")
        return BACKENDS[self.project_type]()


# --------------------------------------------------------------------------
# Shared steps
# --------------------------------------------------------------------------


def mirror_workspace(config: Config, backend: Backend, version: str) -> None:
    for package in config.workspace_packages:
        log(f"Mirroring version {version} onto workspace package {package}")
        run(backend.workspace_command(package, version), capture=True)


def refresh_lock(config: Config, backend: Backend) -> None:
    if not config.run_lock:
        return
    run(backend.lock_command())


def run_pre_commit_command(config: Config) -> None:
    if not config.pre_commit_command:
        return
    log("Running pre-commit command")
    run(["bash", "-c", config.pre_commit_command])


def commit(config: Config, message: str) -> None:
    command = ["git", "commit"]
    if config.commit_skip_hooks:
        command.append("-n")
    command += ["-a", "-m", message]
    run(command)


# --------------------------------------------------------------------------
# Phases
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Release:
    base_version: str
    new_version: str
    is_prerelease: bool


def tag_release(config: Config, backend: Backend) -> Release:
    """Bump the version, build the changelog, then commit, tag and push."""
    base_version = backend.read_version()
    log(f"Bumping from version {base_version}")

    with group("Bump version"):
        run(backend.bump_command(config.bump_segments))
        new_version = backend.read_version()
        log(f"Bumped to version {new_version}")
        mirror_workspace(config, backend, new_version)
        refresh_lock(config, backend)

    with group("Update changelog"):
        if config.update_changelog:
            run(backend.changelog_command(new_version))
        else:
            log("Skipping changelog update")

    with group("Commit and tag"):
        run_pre_commit_command(config)
        commit(config, f"bump: version {base_version} -> {new_version}")
        run(["git", "tag", f"v{new_version}"])
        if config.do_push:
            run(["git", "push"])
            run(["git", "push", "--tags"])

    return Release(
        base_version=base_version,
        new_version=new_version,
        is_prerelease=backend.is_prerelease(new_version),
    )


def land_prerelease(config: Config, backend: Backend, release: Release) -> str | None:
    """Land a second commit moving the branch onto a pre-release version.

    Returns the new pre-release version, or None when the bump was skipped.
    """
    if config.pre_release_bump == NONE:
        log("Skipping pre-release bump (pre-release-bump=none)")
        return None
    if release.is_prerelease:
        log("Skipping pre-release bump; tagged version is already a pre-release")
        return None

    with group("Bump onto pre-release"):
        run(
            backend.prerelease_command(config.pre_release_base, config.pre_release_bump)
        )
        dev_version = backend.read_version()
        log(f"Bumping main onto pre-release {release.new_version} > {dev_version}")

        mirror_workspace(config, backend, dev_version)
        refresh_lock(config, backend)
        run_pre_commit_command(config)

        label = backend.prerelease_label(config.pre_release_bump, dev_version)
        commit(
            config,
            f"bump({label}): version {release.new_version} > {dev_version}",
        )
        if config.do_push:
            run(["git", "push"])

    return dev_version


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main() -> int:
    try:
        config = Config.from_env()
        backend = config.backend()

        release = tag_release(config, backend)

        # Published before the pre-release phase so a failure there still
        # leaves the tagged release's outputs available to later steps.
        write_output("base-version", release.base_version)
        write_output("new-version", release.new_version)
        write_output("tag", f"v{release.new_version}")
        write_output("is-prerelease", str(release.is_prerelease).lower())

        dev_version = land_prerelease(config, backend, release)
        if dev_version is not None:
            write_output("dev-version", dev_version)
    except BumpError as error:
        log(f"::error::{error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
