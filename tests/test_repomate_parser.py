"""Tests for repomate.utils.parser — code parsing across languages."""

from __future__ import annotations

import textwrap

from repomate.utils.parser import (
    _parse_python_ast,
    _parse_with_regex,
    detect_language,
    parse_file,
)


class TestDetectLanguage:
    def test_python(self):
        assert detect_language("file.py") == "python"
        assert detect_language("path/to/module.py") == "python"

    def test_typescript(self):
        assert detect_language("component.ts") == "typescript"
        assert detect_language("component.tsx") == "typescript"

    def test_javascript(self):
        assert detect_language("app.js") == "javascript"
        assert detect_language("app.jsx") == "javascript"

    def test_go(self):
        assert detect_language("main.go") == "go"

    def test_rust(self):
        assert detect_language("lib.rs") == "rust"

    def test_java(self):
        assert detect_language("Main.java") == "java"

    def test_unknown(self):
        assert detect_language("Makefile") == "unknown"
        assert detect_language("script.sh") == "unknown"


class TestParsePythonAST:
    def test_simple_function(self):
        source = textwrap.dedent("""\
            def hello(name: str) -> str:
                return f"Hello, {name}"
        """)
        result = _parse_python_ast(source, "test.py", False)
        assert result["language"] == "python"
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "hello"
        assert result["functions"][0]["line"] == 1
        assert result["functions"][0]["args"][0]["name"] == "name"
        assert result["functions"][0]["args"][0]["type"] == "str"

    def test_class_with_methods(self):
        source = textwrap.dedent("""\
            class Calculator:
                \"\"\"A simple calculator.\"\"\"
                def add(self, a: int, b: int) -> int:
                    return a + b

                def subtract(self, a, b):
                    return a - b
        """)
        result = _parse_python_ast(source, "calc.py", False)
        assert len(result["classes"]) == 1
        cls = result["classes"][0]
        assert cls["name"] == "Calculator"
        assert cls["docstring"] == "A simple calculator."
        assert len(cls["methods"]) == 2
        assert cls["methods"][0]["name"] == "add"
        assert cls["methods"][1]["name"] == "subtract"

    def test_imports(self):
        source = textwrap.dedent("""\
            import os
            import json as j
            from pathlib import Path
            from typing import Optional, List
            from .utils import helper
        """)
        result = _parse_python_ast(source, "imports.py", False)
        # from typing import Optional, List → 2 entries; total = 6
        assert len(result["imports"]) == 6
        names = [i["name"] for i in result["imports"]]
        assert "os" in names
        assert "json" in names
        assert "pathlib.Path" in names
        assert "typing.Optional" in names

    def test_imports_with_deps(self, tmp_path):
        source = textwrap.dedent("""\
            from repomate.utils.parser import parse_file
            from nanobot.agent.loop import AgentLoop
            import requests
        """)
        # Create a fake module directory so internal dep resolution works
        (tmp_path / "repomate").mkdir()
        test_path = str(tmp_path / "main.py")
        result = _parse_python_ast(source, test_path, include_dependencies=True)
        # repomate exists as a directory, nanobot does not (so it's external)
        assert "repomate.utils.parser" in result.get("internal_deps", [])
        assert "nanobot.agent.loop" in result.get("external_deps", [])
        assert "requests" in result.get("external_deps", [])

    def test_top_level_constants(self):
        source = textwrap.dedent("""\
            MAX_RETRIES = 3
            TIMEOUT = 30.0
            local_var = "not constant"
        """)
        result = _parse_python_ast(source, "consts.py", False)
        constant_names = [c["name"] for c in result["top_level_constants"]]
        assert "MAX_RETRIES" in constant_names
        assert "TIMEOUT" in constant_names
        assert "local_var" not in constant_names

    def test_decorators(self):
        source = textwrap.dedent("""\
            @staticmethod
            @cache_result
            def cached_lookup(key: str) -> dict:
                return {}
        """)
        result = _parse_python_ast(source, "deco.py", False)
        func = result["functions"][0]
        assert "staticmethod" in func["decorators"]
        assert "cache_result" in func["decorators"]

    def test_async_function(self):
        source = textwrap.dedent("""\
            async def fetch_data(url: str) -> dict:
                return {"data": "ok"}
        """)
        result = _parse_python_ast(source, "async_test.py", False)
        assert result["functions"][0]["is_async"] is True

    def test_syntax_error(self):
        source = "def broken(:"
        result = _parse_python_ast(source, "broken.py", False)
        assert "error" in result

    def test_class_bases(self):
        source = textwrap.dedent("""\
            class MyTool(BaseTool, Protocol):
                pass
        """)
        result = _parse_python_ast(source, "bases.py", False)
        assert "BaseTool" in result["classes"][0]["bases"]
        assert "Protocol" in result["classes"][0]["bases"]


class TestParseFileIntegration:
    def test_parse_existing_file(self, tmp_path):
        f = tmp_path / "hello.py"
        f.write_text(textwrap.dedent("""\
            import sys

            def main():
                print("hello")
        """))
        result = parse_file(str(f))
        assert result["language"] == "python"
        assert result["total_lines"] == 4
        assert len(result["functions"]) == 1


class TestRegexFallback:
    def test_typescript_class_and_function(self):
        source = textwrap.dedent("""\
            export class AuthService {
                authenticate(token: string): boolean {
                    return true;
                }
            }
            export async function initApp(): Promise<void> {
                console.log("init");
            }
        """)
        result = _parse_with_regex(source, "auth.ts", "typescript", False)
        assert result["language"] == "typescript"
        assert result["parser"] == "regex"
        class_names = [c["name"] for c in result["classes"]]
        function_names = [f["name"] for f in result["functions"]]
        assert "AuthService" in class_names
        assert "initApp" in function_names

    def test_go_struct_and_func(self):
        source = textwrap.dedent("""\
            type User struct {
                Name string
                Age  int
            }
            func NewUser(name string) *User {
                return &User{Name: name}
            }
        """)
        result = _parse_with_regex(source, "user.go", "go", False)
        assert result["language"] == "go"
        assert any(c["name"] == "User" for c in result["classes"])
        assert any(f["name"] == "NewUser" for f in result["functions"])
