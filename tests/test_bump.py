"""Unit tests for the bump-version script's decision logic.

These cover the parts that decide *what* to run — argument assembly, version
classification and input parsing — rather than the subprocess plumbing.
"""

import pytest
from conftest import bump


@pytest.fixture
def uv() -> bump.UvBackend:
    return bump.UvBackend()


@pytest.fixture
def yarn() -> bump.YarnBackend:
    return bump.YarnBackend()


class TestUvBumpCommands:
    def test_single_segment(self, uv):
        assert uv.bump_command(["patch"]) == [
            "uv", "version", "--frozen", "--bump", "patch",
        ]

    def test_each_segment_becomes_its_own_bump_flag(self, uv):
        assert uv.bump_command(["minor", "alpha"]) == [
            "uv", "version", "--frozen", "--bump", "minor", "--bump", "alpha",
        ]

    def test_prerelease_applies_base_then_bump(self, uv):
        assert uv.prerelease_command("patch", "dev") == [
            "uv", "version", "--frozen", "--bump", "patch", "--bump", "dev",
        ]

    def test_prerelease_base_none_is_skipped(self, uv):
        assert uv.prerelease_command("none", "dev") == [
            "uv", "version", "--frozen", "--bump", "dev",
        ]

    def test_workspace_pins_exact_version(self, uv):
        assert uv.workspace_command("bookshelf", "1.2.3") == [
            "uv", "version", "--frozen", "--package", "bookshelf", "1.2.3",
        ]

    def test_changelog_uses_project_environment(self, uv):
        assert uv.changelog_command("1.2.3") == [
            "uv", "run", "towncrier", "build", "--yes", "--version", "v1.2.3",
        ]


class TestYarnBumpCommands:
    def test_segments_pass_through_verbatim(self, yarn):
        assert yarn.bump_command(["preminor", "--preid", "alpha"]) == [
            "npm", "version", "preminor", "--preid", "alpha", "--no-git-tag-version",
        ]

    def test_prerelease_concatenates_base_and_bump_words(self, yarn):
        assert yarn.prerelease_command("prepatch", "--preid dev") == [
            "npm", "version", "prepatch", "--preid", "dev", "--no-git-tag-version",
        ]

    def test_prerelease_base_none_is_skipped(self, yarn):
        assert yarn.prerelease_command("none", "prerelease --preid rc") == [
            "npm", "version", "prerelease", "--preid", "rc", "--no-git-tag-version",
        ]

    def test_workspace_targets_package_directory(self, yarn):
        assert yarn.workspace_command("apps/portal", "1.2.3") == [
            "npm", "version", "--no-git-tag-version",
            "--prefix", "apps/portal", "1.2.3",
        ]

    def test_changelog_fetches_towncrier_on_the_fly(self, yarn):
        assert yarn.changelog_command("1.2.3") == [
            "uvx", "towncrier", "build", "--yes", "--version", "v1.2.3",
        ]


class TestUvPrereleaseDetection:
    @pytest.mark.parametrize(
        "version", ["1.2.3a1", "1.2.3b2", "1.2.3rc1", "1.2.4.dev0", "2.0.0a0"]
    )
    def test_prerelease_versions(self, uv, version):
        assert uv.is_prerelease(version) is True

    @pytest.mark.parametrize("version", ["1.2.3", "0.1.0", "10.20.30"])
    def test_stable_versions(self, uv, version):
        assert uv.is_prerelease(version) is False

    @pytest.mark.parametrize("version", ["1.2.3+abc", "1.2.3+build.5", "1.2.3+deb1"])
    def test_local_version_segments_are_not_prereleases(self, uv, version):
        # The previous shell implementation matched a bare `a`, `b`, `rc` or
        # `dev` anywhere in the string, so these were misread as pre-releases
        # and silently skipped both the dev bump and the GitHub release.
        assert uv.is_prerelease(version) is False

    def test_invalid_version_is_reported(self, uv):
        with pytest.raises(bump.BumpError, match="not a valid PEP 440 version"):
            uv.is_prerelease("not-a-version")


class TestYarnPrereleaseDetection:
    @pytest.mark.parametrize("version", ["1.2.3-alpha.0", "1.2.3-rc.1", "1.2.3-dev.0"])
    def test_prerelease_versions(self, yarn, version):
        assert yarn.is_prerelease(version) is True

    @pytest.mark.parametrize("version", ["1.2.3", "0.1.0"])
    def test_stable_versions(self, yarn, version):
        assert yarn.is_prerelease(version) is False

    def test_hyphen_in_build_metadata_is_not_a_prerelease(self, yarn):
        assert yarn.is_prerelease("1.2.3+build-5") is False


class TestPrereleaseLabel:
    """The scope of the second commit's `bump(<label>): ...` message."""

    @pytest.mark.parametrize(
        ("requested", "version"),
        [("dev", "1.2.5.dev1"), ("alpha", "1.3.0a1"), ("rc", "1.3.0rc1")],
    )
    def test_uv_uses_the_requested_word(self, uv, requested, version):
        assert uv.prerelease_label(requested, version) == requested

    @pytest.mark.parametrize(
        ("requested", "version", "expected"),
        [
            ("--preid dev", "1.2.5-dev.0", "dev"),
            ("prerelease --preid rc", "1.2.4-rc.0", "rc"),
            ("--preid alpha", "2.0.0-alpha.12", "alpha"),
        ],
    )
    def test_yarn_reads_the_identifier_off_the_version(
        self, yarn, requested, version, expected
    ):
        # Using the raw input would give a scope like `bump(--preid dev)`.
        assert yarn.prerelease_label(requested, version) == expected

    def test_yarn_falls_back_when_no_preid_was_given(self, yarn):
        assert yarn.prerelease_label("prerelease", "1.2.4-0") == "prerelease"

    def test_yarn_ignores_build_metadata(self, yarn):
        assert yarn.prerelease_label("--preid dev", "1.2.5-dev.0+build-7") == "dev"


class TestConfig:
    def test_defaults_match_the_action_inputs(self):
        config = bump.Config.from_env({"BUMP_RULE": "patch"})
        assert config.project_type == "uv"
        assert config.pre_release_base == "patch"
        assert config.pre_release_bump == "dev"
        assert config.update_changelog is True
        assert config.run_lock is True
        assert config.do_push is True
        assert config.commit_skip_hooks is False
        assert config.workspace_packages == ()

    def test_booleans_only_true_enables(self):
        config = bump.Config.from_env(
            {"BUMP_RULE": "patch", "UPDATE_CHANGELOG": "false", "DO_PUSH": "no"}
        )
        assert config.update_changelog is False
        assert config.do_push is False

    def test_workspace_packages_split_on_newlines(self):
        config = bump.Config.from_env(
            {"BUMP_RULE": "patch", "WORKSPACE_PACKAGES": "  one \n\n two\n"}
        )
        assert config.workspace_packages == ("one", "two")

    def test_bump_rule_splits_on_whitespace(self):
        config = bump.Config.from_env({"BUMP_RULE": " minor  alpha "})
        assert config.bump_segments == ["minor", "alpha"]

    def test_backend_selected_by_project_type(self):
        uv_config = bump.Config.from_env({"BUMP_RULE": "patch"})
        yarn_config = bump.Config.from_env(
            {"BUMP_RULE": "patch", "PROJECT_TYPE": "yarn"}
        )
        assert isinstance(uv_config.backend(), bump.UvBackend)
        assert isinstance(yarn_config.backend(), bump.YarnBackend)

    def test_unknown_project_type_is_rejected(self):
        config = bump.Config.from_env({"BUMP_RULE": "patch", "PROJECT_TYPE": "poetry"})
        with pytest.raises(bump.BumpError, match="project-type must be one of"):
            config.backend()

    def test_empty_bump_rule_is_rejected(self):
        config = bump.Config.from_env({"BUMP_RULE": "   "})
        with pytest.raises(bump.BumpError, match="bump-rule must not be empty"):
            config.backend()
