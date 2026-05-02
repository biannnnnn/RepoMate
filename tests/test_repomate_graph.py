"""Tests for repomate.utils.graph — dependency graph construction."""

from __future__ import annotations

from repomate.utils.graph import (
    _classify_file,
    _file_to_node,
    _find_circular_deps,
    _resolve_dep_to_path,
)


class TestClassifyFile:
    def test_test_files(self):
        assert _classify_file("tests/test_auth.py") == "test"
        assert _classify_file("src/auth_test.py") == "test"
        assert _classify_file("components/Login.test.ts") == "test"
        assert _classify_file("spec/user_spec.rb") == "test"

    def test_config_files(self):
        assert _classify_file("config/settings.py") == "config"
        assert _classify_file("conf/database.yml") == "config"

    def test_interface_files(self):
        assert _classify_file("cli/main.py") == "interface"
        assert _classify_file("commands/user.py") == "interface"

    def test_utility_files(self):
        assert _classify_file("utils/helpers.py") == "utility"
        assert _classify_file("common/validators.py") == "utility"
        assert _classify_file("shared/constants.py") == "utility"

    def test_package_init(self):
        assert _classify_file("nanobot/__init__.py") == "package"

    def test_core_by_default(self):
        assert _classify_file("src/models/user.py") == "core"
        assert _classify_file("lib/services.py") == "core"


class TestFileToNode:
    def test_basic(self):
        node = _file_to_node("src/models/user.py", None)
        assert node["path"] == "src/models/user.py"
        assert node["name"] == "user.py"
        assert node["directory"] == "src/models"
        assert node["category"] == "core"


class TestResolveDepToPath:
    def test_direct_py(self):
        deps = {"nanobot/agent/loop.py": [], "nanobot/agent/hook.py": []}
        resolved = _resolve_dep_to_path("nanobot.agent.hook", ("nanobot", "agent"), deps)
        assert resolved == "nanobot/agent/hook.py"

    def test_init_py(self):
        deps = {"nanobot/__init__.py": [], "nanobot/agent/__init__.py": []}
        resolved = _resolve_dep_to_path("nanobot", ("src",), deps)
        assert resolved == "nanobot/__init__.py"

    def test_relative_import(self):
        deps = {"nanobot/agent/tools/base.py": []}
        resolved = _resolve_dep_to_path(
            ".tools.base", ("nanobot", "agent"), deps
        )
        # Relative resolution depends on directory structure
        assert isinstance(resolved, str)


class TestFindCircularDeps:
    def test_no_cycles(self):
        deps = {
            "a.py": ["b.py"],
            "b.py": ["c.py"],
            "c.py": [],
        }
        cycles = _find_circular_deps(deps)
        assert len(cycles) == 0

    def test_simple_cycle(self):
        deps = {
            "a.py": ["b.py"],
            "b.py": ["a.py"],
        }
        cycles = _find_circular_deps(deps)
        assert len(cycles) >= 1

    def test_three_node_cycle(self):
        deps = {
            "a.py": ["b.py"],
            "b.py": ["c.py"],
            "c.py": ["a.py"],
        }
        cycles = _find_circular_deps(deps)
        assert len(cycles) >= 1


class TestBuildDependencyGraph:
    def test_mermaid_format(self, tmp_path):
        """Test that build_dependency_graph works on a small repo."""
        import os
        from repomate.utils.graph import build_dependency_graph

        # Create a tiny repo
        (tmp_path / "main.py").write_text("from utils import helper\n\ndef main():\n    helper.run()\n")
        (tmp_path / "utils").mkdir()
        (tmp_path / "utils" / "__init__.py").write_text("")
        (tmp_path / "utils" / "helper.py").write_text("def run():\n    print('running')\n")
        os.chdir(tmp_path)

        result = build_dependency_graph(str(tmp_path), format="mermaid")
        assert result["files"] >= 2
        assert "mermaid" in result
        assert len(result["errors"]) == 0

    def test_json_format(self, tmp_path):
        from repomate.utils.graph import build_dependency_graph

        (tmp_path / "main.py").write_text("print('hello')\n")

        result = build_dependency_graph(str(tmp_path), format="json")
        assert "graph" in result
        assert result["files"] == 1

    def test_dot_format(self, tmp_path):
        from repomate.utils.graph import build_dependency_graph

        (tmp_path / "main.py").write_text("import sys\nprint('hello')\n")

        result = build_dependency_graph(str(tmp_path), format="dot")
        assert "dot" in result
        assert "digraph" in result["dot"]

    def test_nonexistent_dir(self):
        from repomate.utils.graph import build_dependency_graph

        result = build_dependency_graph("/nonexistent/path")
        assert "error" in result
