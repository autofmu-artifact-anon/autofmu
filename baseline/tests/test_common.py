"""Tests for baseline/common/paths.py and workspace.py."""

from pathlib import Path
import baseline.common.workspace as workspace_module
import pytest

from baseline.common import (
    METHOD_NAMES,
    METHOD_SPECS,
    method_spec,
    baseline_root,
    method_workspace,
    workspaces_root,
    evaluator_runs_root,
    bootstrap_method_workspace,
    ensure_workspace_subdir,
    validate_path_in_workspace,
    WorkspaceError,
    safe_write,
    safe_read,
    list_workspace_files,
    workspace_exists,
    repo_root,
    get_workspace_readme_content,
)


class TestPaths:
    """Tests for paths.py helpers."""

    def test_repo_root_contains_expected_dirs(self) -> None:
        """Repo root should contain baseline and evaluator directories."""
        root = repo_root()
        assert root.is_dir()
        assert (root / "baseline").is_dir()
        assert (root / "evaluator").is_dir()

    def test_baseline_root(self) -> None:
        """baseline_root should point to baseline/ under repo root."""
        path = baseline_root()
        assert path.name == "baseline"
        assert path.is_dir()

    def test_workspaces_root(self) -> None:
        """workspaces_root should point to baseline/workspaces/."""
        path = workspaces_root()
        assert path.name == "workspaces"
        assert path.is_dir()

    def test_evaluator_runs_root(self) -> None:
        """evaluator_runs_root should point to evaluator/runs/."""
        path = evaluator_runs_root()
        assert path.name == "runs"
        assert path.parent.name == "evaluator"

    def test_method_workspace_valid_names(self) -> None:
        """method_workspace should return paths for valid method names."""
        for name in METHOD_NAMES:
            path = method_workspace(name)
            assert path.name == name
            assert path.parent.name == "workspaces"

    def test_method_workspace_invalid_name(self) -> None:
        """method_workspace should raise ValueError for invalid names."""
        with pytest.raises(ValueError, match="Unknown method name"):
            method_workspace("invalid_method_xyz")


class TestWorkspace:
    """Tests for workspace.py helpers."""

    def test_bootstrap_creates_workspace_root(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """bootstrap_method_workspace should always create the method root."""
        method_name = "baseline_b1_rule_sequential"
        workspace = tmp_path / method_name
        monkeypatch.setattr(workspace_module, "method_workspace", lambda _: workspace)

        path = bootstrap_method_workspace(method_name)

        assert path == workspace
        assert path.is_dir()
        assert not (path / "prompts").exists()

    def test_bootstrap_creates_standard_subdirs(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """bootstrap_method_workspace should create directories when requested."""
        method_name = "baseline_b1_rule_sequential"
        workspace = tmp_path / method_name
        monkeypatch.setattr(workspace_module, "method_workspace", lambda _: workspace)

        path = bootstrap_method_workspace(method_name, create_subdirs=True)
        assert path.is_dir()
        assert (path / "prompts").exists()
        assert (path / "runs").exists()
        assert (path / "cache").exists()
        assert (path / "fixtures").exists()

    def test_ensure_workspace_subdir(self) -> None:
        """ensure_workspace_subdir should create subdirectories."""
        method_name = "baseline_b1_rule_sequential"
        path = ensure_workspace_subdir(method_name, "cache")
        assert path.exists()
        assert path.name == "cache"

    def test_ensure_workspace_invalid_subdir(self) -> None:
        """ensure_workspace_subdir should reject invalid subdirs."""
        with pytest.raises(ValueError, match="Invalid workspace subdir"):
            ensure_workspace_subdir("baseline_b1_rule_sequential", "invalid_subdir")

    def test_validate_path_in_workspace(self) -> None:
        """validate_path_in_workspace should accept absolute paths inside workspace."""
        method_name = "baseline_b1_rule_sequential"
        workspace = method_workspace(method_name)
        valid_path = workspace / "prompts" / "test.txt"
        result = validate_path_in_workspace(method_name, valid_path)
        assert result == valid_path.resolve()

    def test_validate_path_in_workspace_resolves_relative_to_workspace(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Relative validation should resolve from the method workspace, not cwd."""
        method_name = "baseline_b1_rule_sequential"
        workspace = method_workspace(method_name).resolve()
        monkeypatch.chdir(tmp_path)

        result = validate_path_in_workspace(method_name, "cache/from-workspace.txt")

        assert result == workspace / "cache" / "from-workspace.txt"

    def test_validate_path_outside_workspace(self) -> None:
        """validate_path_in_workspace should reject paths outside workspace."""
        method_name = "baseline_b1_rule_sequential"
        outside_path = Path("/tmp/outside_workspace.txt")
        with pytest.raises(WorkspaceError, match="escapes workspace"):
            validate_path_in_workspace(method_name, outside_path)

    def test_validate_path_blocks_relative_escape(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Relative paths that traverse upward should be rejected deterministically."""
        method_name = "baseline_b1_rule_sequential"
        monkeypatch.chdir(tmp_path)

        with pytest.raises(WorkspaceError, match="escapes workspace"):
            validate_path_in_workspace(method_name, "../../../tmp/escaped.txt")

    def test_safe_write_and_read(self) -> None:
        """safe_write and safe_read should work correctly."""
        method_name = "baseline_b1_rule_sequential"
        relative_path = "cache/test_write.txt"
        content = "Hello, workspace!"

        # Write
        written_path = safe_write(method_name, relative_path, content)
        assert written_path.exists()

        # Read
        read_content = safe_read(method_name, relative_path)
        assert read_content == content

        # Cleanup
        written_path.unlink()

    def test_safe_write_blocks_escape(self) -> None:
        """safe_write should reject paths that escape workspace."""
        method_name = "baseline_b1_rule_sequential"
        # Try to escape with ..
        relative_path = "../../../tmp/escaped.txt"
        with pytest.raises(WorkspaceError, match="escapes workspace"):
            safe_write(method_name, relative_path, "malicious content")

    def test_safe_read_blocks_escape(self) -> None:
        """safe_read should reject paths that escape workspace."""
        method_name = "baseline_b1_rule_sequential"

        with pytest.raises(WorkspaceError, match="escapes workspace"):
            safe_read(method_name, "../../../tmp/escaped.txt")

    def test_list_workspace_files(self) -> None:
        """list_workspace_files should return files in workspace."""
        method_name = "baseline_b1_rule_sequential"
        # Create a test file
        test_file = ensure_workspace_subdir(method_name, "cache") / "list_test.txt"
        test_file.write_text("test")

        files = list_workspace_files(method_name, "cache")
        assert any(f.name == "list_test.txt" for f in files)

        # Cleanup
        test_file.unlink()

    def test_workspace_exists(self) -> None:
        """workspace_exists should return correct status."""
        assert workspace_exists("baseline_b1_rule_sequential") is True
        # Invalid method name would raise ValueError before workspace_exists


class TestIntegration:
    """Integration tests for paths + workspace."""

    def test_all_method_workspaces_exist(self) -> None:
        """All 12 method workspaces should exist."""
        for name in METHOD_NAMES:
            assert workspace_exists(name), f"Workspace missing for {name}"

    def test_method_count(self) -> None:
        """There should be exactly 12 methods."""
        assert len(METHOD_NAMES) == 12

    def test_method_specs_cover_all_methods(self) -> None:
        """Naming metadata should cover exactly the known methods."""
        assert tuple(METHOD_SPECS) == METHOD_NAMES

    def test_workspace_readme_content_uses_method_spec(self) -> None:
        """Workspace README content should include the method title and stage matrix."""
        spec = method_spec("baseline_b2_llm_retrieval_rule")
        content = get_workspace_readme_content(spec.name)

        assert spec.title in content
        assert f"- Stage 1: `{spec.stage1_key}`" in content
        assert f"- Stage 2: `{spec.stage2_key}`" in content
        assert f"- Stage 3: `{spec.stage3_key}`" in content
