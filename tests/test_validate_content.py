"""Regression tests for publishable content and safe whitelist installation."""

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_content", ROOT / "scripts/validate_content.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ContentTests(unittest.TestCase):
    def setUp(self):
        # Keep all test writes inside the repository, including on Windows.
        self.temp = tempfile.TemporaryDirectory(prefix=".validation-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repository"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            ".validation-*", "__pycache__", ".git"))

    def replace(self, relative, old, new):
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def schema_mutation(self, name, mutate):
        path = self.root / ("schemas/" + name + "-output.schema.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def assert_invalid(self, expected):
        errors = validator.validate(self.root)
        self.assertTrue(errors)
        self.assertTrue(any(expected in error for error in errors), errors)

    def example_mutation(self, mutate, name="basic-flow"):
        path = self.root / ("examples/" + name + ".md")
        text = path.read_text(encoding="utf-8")
        prefix, rest = text.split("```json\n", 1)
        body, suffix = rest.split("\n```", 1)
        data = json.loads(body)
        mutate(data)
        path.write_text(prefix + "```json\n" + json.dumps(data, ensure_ascii=False, indent=2) +
                        "\n```" + suffix, encoding="utf-8")

    def test_sensitive_append_to_validator_and_test_sources(self):
        fixtures = [("absolute local path", "C:" + "\\Users\\private-user\\data.txt"),
                    ("model UUID", "12345678" + "-1234-1234-1234-123456789abc"),
                    ("credential", "ghp_" + "z" * 25),
                    ("runtime record", "sess" + "_" + "private-record")]
        for relative in ("scripts/validate_content.py", "tests/test_validate_content.py"):
            path = self.root / relative
            original = path.read_text(encoding="utf-8")
            for label, fixture in fixtures:
                with self.subTest(file=relative, pattern=label):
                    path.write_text(original + "\n# " + fixture + "\n", encoding="utf-8")
                    errors = validator.validate(self.root)
                    self.assertTrue(any(relative + ": forbidden " + label in error for error in errors), errors)
            path.write_text(original, encoding="utf-8")

    def test_example_empty_and_missing_envelope_fields(self):
        for field in (None, "iteration", "final_status", "discriminator_output",
                      "writer_output", "reviewer_output", "test_generator_output", "test_run"):
            with self.subTest(field=field):
                path = self.root / "examples/basic-flow.md"
                original = path.read_text(encoding="utf-8")
                self.example_mutation(lambda data: data.clear() if field is None else data.pop(field))
                self.assert_invalid("example envelope missing required fields")
                path.write_text(original, encoding="utf-8")

    def test_in_progress_retry_requires_explicit_null_final_status(self):
        self.example_mutation(lambda data: data.update(iteration=1, final_status=None), "retry-reviewer")
        self.assertEqual([], validator.validate(self.root))

    def test_retry_owner_target_mismatch(self):
        self.example_mutation(lambda data: data["discriminator_output"]["next_action"].update(
            target_agent="code-writer"), "retry-reviewer")
        self.assert_invalid("retry target must match a blocking issue owner")

    def test_user_retry_cannot_stay_in_progress(self):
        self.example_mutation(lambda data: data.update(final_status=None), "human-review-required")
        self.assert_invalid("inconsistent workflow final_status")

    def test_memory_template_rejects_injected_principle(self):
        self.replace("zcode/loop/memory/code-writer.example.md", "## 已批准原则\n",
                     "## 已批准原则\n\n- 注入的实际原则。\n")
        self.assert_invalid("exact empty template")

    def test_python_cache_directory_and_file_rejected(self):
        directory = self.root / "__pycache__"
        directory.mkdir()
        self.assert_invalid("forbidden Python bytecode cache")
        (self.root / "unrelated.pyc").write_bytes(b"synthetic cache")
        errors = validator.validate(self.root)
        self.assertTrue(any("unrelated.pyc" in error for error in errors), errors)

    def test_reviewer_empty_allof_rejected(self):
        self.schema_mutation("reviewer", lambda data: data.update(allOf=[{}]))
        self.assert_invalid("reviewer blocking conditions")

    def test_nested_schema_field_mutations(self):
        cases = [
            ("reviewer", "finding", "problem", "type", "number"),
            ("reviewer", "finding", "file", "minLength", 0),
            ("reviewer", "finding", "severity", "enum", ["minor"]),
            ("reviewer", "finding", "line", "minimum", 0),
            ("test-generator", "scenario", "expected_result", "type", "number"),
            ("test-generator", "scenario", "scenario", "minLength", 0),
            ("test-generator", "scenario", "priority", "enum", ["P9"]),
            ("test-generator", "scenario", "steps", "minItems", 0),
            ("discriminator", "issue", "issue", "type", "number"),
            ("discriminator", "issue", "required_action", "minLength", 0),
            ("discriminator", "issue", "owner", "enum", ["user"]),
            ("discriminator", "action", "instruction", "type", "number"),
            ("discriminator", "action", "instruction", "minLength", 0),
            ("discriminator", "action", "target_agent", "enum", ["user"]),
            ("discriminator", "proposal", "principle", "type", "number"),
            ("discriminator", "proposal", "evidence", "minLength", 0),
        ]
        for name, definition, field, key, value in cases:
            with self.subTest(schema=name, definition=definition, field=field, key=key):
                path = self.root / ("schemas/" + name + "-output.schema.json")
                original = path.read_text(encoding="utf-8")
                self.schema_mutation(name, lambda data: data["$defs"][definition]["properties"][field].update({key: value}))
                self.assert_invalid("invalid nested field types")
                path.write_text(original, encoding="utf-8")

    def test_test_run_strict_negative_cases(self):
        changes = [
            {"summary": ""}, {"summary": 42}, {"summary": "   "},
            {"status": "failed", "exit_codes": [0], "reason": "failure"},
            {"status": "failed", "exit_codes": [1], "reason": None},
            {"status": "failed", "commands": [], "exit_codes": [], "reason": "failure"},
            {"status": "failed", "exit_codes": [1], "reason": 123},
            {"status": "passed", "exit_codes": [1]},
            {"status": "passed", "commands": [], "exit_codes": []},
            {"status": "tests_not_run", "reason": "not available"},
            {"status": "tests_not_run", "commands": [], "exit_codes": [], "reason": ""},
        ]
        for change in changes:
            with self.subTest(change=change):
                path = self.root / "examples/basic-flow.md"
                original = path.read_text(encoding="utf-8")
                self.example_mutation(lambda data: data["test_run"].update(change))
                errors = validator.validate(self.root)
                self.assertTrue(any("TEST_RUN" in error or "requires" in error for error in errors), errors)
                path.write_text(original, encoding="utf-8")

    def test_valid_failed_test_run_evidence(self):
        evidence = {"status": "failed", "commands": ["python -m unittest"], "exit_codes": [1],
                    "summary": "A synthetic assertion failed", "reason": "Unexpected result"}
        self.assertEqual([], validator.check_test_run(evidence))

    def test_repository_passes_including_pattern_definitions(self):
        self.assertEqual([], validator.validate(self.root))

    def test_required_file_missing(self):
        (self.root / "LICENSE").unlink()
        self.assert_invalid("missing required file")

    def test_skill_frontmatter_missing(self):
        self.replace("zcode/skills/loop-engine/SKILL.md", "---\nname: loop-engine", "name: loop-engine")
        self.assert_invalid("missing frontmatter")

    def test_skill_description_missing(self):
        path = self.root / "zcode/skills/loop-engine/SKILL.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(line for line in lines if not line.startswith("description:")), encoding="utf-8")
        self.assert_invalid("nonempty description")

    def test_agent_model_binding_rejected(self):
        self.replace("zcode/agents/code-writer.md", "name: code-writer", "name: code-writer\nmodel: local-model")
        self.assert_invalid("frontmatter requires")

    def test_state_typo(self):
        self.replace("zcode/skills/loop-engine/SKILL.md", "TEST_GENERATE", "TEST_GENRATE")
        self.assert_invalid("required role/stage/status")

    def test_reviewer_retry_must_include_downstream_stages(self):
        self.replace("zcode/commands/loop-engine.md",
                     "retry target=code-reviewer -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE",
                     "retry target=code-reviewer -> REVIEW -> DISCRIMINATE")
        self.assert_invalid("retry transition")

    def test_absolute_local_path(self):
        with (self.root / "README.md").open("a", encoding="utf-8") as stream:
            stream.write("\n" + "C:" + "\\Users\\local-user\\private.txt\n")
        self.assert_invalid("absolute local path")

    def test_posix_local_path(self):
        with (self.root / "README.md").open("a", encoding="utf-8") as stream:
            stream.write("\n" + "/ho" + "me/local-user/private.txt\n")
        self.assert_invalid("absolute local path")

    def test_uuid_credential_and_record_patterns(self):
        values = ["12345678" + "-1234-1234-1234-123456789abc",
                  "ghp_" + "a" * 25, "sess" + "_" + "fictional123"]
        for index, value in enumerate(values):
            (self.root / ("docs/negative-" + str(index) + ".md")).write_text(value, encoding="utf-8")
        errors = validator.validate(self.root)
        for label in ("model UUID", "credential", "runtime record"):
            self.assertTrue(any(label in error for error in errors), errors)

    def test_memory_explicit_confirmation_missing(self):
        self.replace("docs/memory-policy.md", "用户明确确认", "用户一般了解")
        self.assert_invalid("Memory approval rule")

    def test_memory_main_session_missing(self):
        self.replace("zcode/agents/discriminator.md", "主会话展示", "自动收集")
        self.assert_invalid("Memory approval rule")

    def test_malformed_schema_json(self):
        (self.root / "schemas/writer-output.schema.json").write_text("{broken", encoding="utf-8")
        self.assert_invalid("invalid JSON schema")

    def test_schema_required_field_missing(self):
        self.schema_mutation("writer", lambda data: data["required"].remove("needs_review"))
        self.assert_invalid("key schema fields")

    def test_schema_property_missing(self):
        self.schema_mutation("test-generator", lambda data: data["properties"].pop("test_commands"))
        self.assert_invalid("required fields must have properties")

    def test_schema_nested_issue_field_missing(self):
        self.schema_mutation("discriminator", lambda data: data["$defs"]["issue"]["required"].remove("required_action"))
        self.assert_invalid("blocking_issues")

    def test_schema_invalid_type(self):
        self.schema_mutation("writer", lambda data: data["properties"]["changed_files"].update(type="nonsense"))
        self.assert_invalid("invalid schema type")

    def test_schema_wrong_verdict(self):
        self.schema_mutation("discriminator", lambda data: data["properties"]["overall_status"]["enum"].append("max_iterations_reached"))
        self.assert_invalid("iteration verdict enum")

    def test_schema_broken_local_ref(self):
        self.schema_mutation("reviewer", lambda data: data["properties"]["non_blocking_findings"]["items"].update({"$ref": "#/$defs/missing"}))
        self.assert_invalid("broken schema reference")

    def test_schema_condition_cannot_be_replaced_by_empty_objects(self):
        self.schema_mutation("discriminator", lambda data: data.update(allOf=[{}, {}, {}, {}]))
        self.assert_invalid("status conditions do not enforce")

    def test_schema_array_items_cannot_be_weakened(self):
        self.schema_mutation("writer", lambda data: data["properties"]["changed_files"].update(items={}))
        self.assert_invalid("nonempty string array items")

    def test_runtime_directory_is_rejected(self):
        path = self.root / ("roll" + "out") / "record.txt"
        path.parent.mkdir()
        path.write_text("Synthetic runtime data", encoding="utf-8")
        self.assert_invalid("runtime directory content")

    def test_invalid_root_is_reported(self):
        self.assertEqual(["repository root is not a directory"], validator.validate(self.root / "missing"))

    def test_example_bad_final_status(self):
        self.replace("examples/retry-reviewer.md", '"final_status": "max_iterations_reached"', '"final_status": "fail"')
        self.assert_invalid("inconsistent workflow final_status")

    def test_example_unrecorded_score_exception(self):
        self.replace("examples/basic-flow.md", '"writer_score": 0.88', '"writer_score": 0.50')
        self.assert_invalid("recorded policy_exceptions")

    def test_example_retry_requires_action(self):
        self.replace("examples/basic-flow.md", '"overall_status": "pass"', '"overall_status": "retry"')
        self.assert_invalid("incorrect type")

    def test_example_unknown_field(self):
        self.replace("examples/basic-flow.md", '"needs_review": true', '"needs_review": true, "unrecognized": true')
        self.assert_invalid("unexpected fields")

    def test_code_fence_unclosed(self):
        with (self.root / "docs/privacy.md").open("a", encoding="utf-8") as stream:
            stream.write("\n```text\nunclosed\n")
        self.assert_invalid("unclosed code fence")

    def test_relative_link_and_anchor(self):
        with (self.root / "README.md").open("a", encoding="utf-8") as stream:
            stream.write("\n[broken](docs/missing.md)\n[anchor](docs/privacy.md#missing)\n")
        self.assert_invalid("broken relative Markdown link")
        self.assert_invalid("missing Markdown anchor")

    def test_cli_from_other_working_directory(self):
        script = self.root / "scripts/validate_content.py"
        for args in ([], ["--root", str(self.root)]):
            completed = subprocess.run([sys.executable, str(script)] + args,
                                       cwd=self.root / "docs", capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)


class ContractTests(unittest.TestCase):
    def test_all_final_state_mappings(self):
        for iteration in (1, 2, 3):
            self.assertEqual("pass", validator.final_status("pass", None, iteration))
            self.assertEqual("fail", validator.final_status("fail", None, iteration))
            self.assertEqual("human_review_required", validator.final_status("human_review_required", "user", iteration))
            self.assertEqual("human_review_required", validator.final_status("retry", "user", iteration))
            for target in validator.ROLES[:3]:
                self.assertEqual("max_iterations_reached" if iteration == 3 else None,
                                 validator.final_status("retry", target, iteration))
        for iteration in (0, 4, True):
            with self.assertRaises(ValueError):
                validator.final_status("retry", "code-writer", iteration)

    def test_reviewer_blocker_cannot_approve(self):
        schema = validator.load_json((ROOT / "schemas/reviewer-output.schema.json").read_text(encoding="utf-8"))
        output = {"verdict": "approve", "risk_assessment": "high", "non_blocking_findings": [],
                  "missed_tests": [], "review_confidence": .9, "blocking_findings": [
                      {"file": "src/example.py", "line": 1, "severity": "major", "problem": "错误结果",
                       "impact": "验收不满足", "suggestion": "修复分支"}]}
        self.assertTrue(validator.validate_instance(output, schema))
        output["verdict"] = "request_changes"
        self.assertEqual([], validator.validate_instance(output, schema))

    def test_discriminator_status_conditions(self):
        schema = validator.load_json((ROOT / "schemas/discriminator-output.schema.json").read_text(encoding="utf-8"))
        _, blocks = validator.markdown_parts((ROOT / "examples/basic-flow.md").read_text(encoding="utf-8"))
        output = validator.load_json(next(body for language, body in blocks if language == "json"))["discriminator_output"]
        for verdict in ("pass", "retry", "human_review_required", "fail"):
            current = copy.deepcopy(output)
            current["overall_status"] = verdict
            current["next_action"] = ({"target_agent": "user" if verdict == "human_review_required" else "code-writer",
                                       "instruction": "核对验收"} if verdict in {"retry", "human_review_required"} else None)
            self.assertEqual([], validator.validate_instance(current, schema))
            current["next_action"] = None if current["next_action"] else {"target_agent": "code-writer", "instruction": "核对"}
            self.assertTrue(validator.validate_instance(current, schema))

    def test_json_duplicate_keys_and_non_finite_values(self):
        for text in ('{"x": 1, "x": 2}', '{"x": NaN}', '{"x": Infinity}'):
            with self.assertRaises(ValueError):
                validator.load_json(text)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".validation-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def available_installers(self):
        installers = []
        bash = shutil.which("bash")
        if bash:
            installers.append(("shell", [bash, str(ROOT / "scripts/install.sh")], "--target", "--force"))
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell:
            installers.append(("powershell", [powershell, "-NoProfile", "-File", str(ROOT / "scripts/install.ps1")], "-Target", "-Force"))
        if not installers:
            self.skipTest("Neither Bash nor PowerShell is available for installer integration tests")
        return installers

    def run_installer(self, command, target_arg, target, extra=()):
        environment = os.environ.copy()
        # Isolate HOME even though the test supplies an explicit target.
        environment["HOME"] = str(self.directory)
        return subprocess.run(command + [target_arg, str(target)] + list(extra),
                              cwd=self.directory, env=environment, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)

    def test_install_whitelist_conflict_preflight_and_force(self):
        for name, command, target_arg, force_arg in self.available_installers():
            with self.subTest(installer=name):
                target = self.directory / name
                conflict = target / validator.INSTALL_FILES[-1]
                conflict.parent.mkdir(parents=True)
                conflict.write_text("custom configuration", encoding="utf-8")
                guard = target / "AGENTS.md"
                guard.write_text("keep user instructions", encoding="utf-8")
                result = self.run_installer(command, target_arg, target)
                self.assertNotEqual(0, result.returncode)
                self.assertFalse((target / "agents").exists(), result.stdout + result.stderr)
                self.assertEqual("custom configuration", conflict.read_text(encoding="utf-8"))
                result = self.run_installer(command, target_arg, target, [force_arg])
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                actual = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
                self.assertEqual(set(validator.INSTALL_FILES) | {"AGENTS.md"}, actual)
                self.assertEqual("keep user instructions", guard.read_text(encoding="utf-8"))
                for relative in validator.INSTALL_FILES:
                    self.assertEqual((ROOT / "zcode" / relative).read_bytes(), (target / relative).read_bytes())
                result = self.run_installer(command, target_arg, target)
                self.assertNotEqual(0, result.returncode)

    def test_clean_install(self):
        for name, command, target_arg, _ in self.available_installers():
            with self.subTest(installer=name):
                target = self.directory / name
                result = self.run_installer(command, target_arg, target)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertEqual(set(validator.INSTALL_FILES),
                                 {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()})

    def test_force_does_not_overwrite_directory(self):
        for name, command, target_arg, force_arg in self.available_installers():
            with self.subTest(installer=name):
                target = self.directory / name
                (target / validator.INSTALL_FILES[-1]).mkdir(parents=True)
                result = self.run_installer(command, target_arg, target, [force_arg])
                self.assertNotEqual(0, result.returncode)
                self.assertFalse((target / "agents").exists())

    def test_force_replaces_hard_link_without_modifying_sentinel(self):
        for name, command, target_arg, force_arg in self.available_installers():
            with self.subTest(installer=name):
                target = self.directory / name
                destination = target / validator.INSTALL_FILES[-1]
                destination.parent.mkdir(parents=True)
                sentinel = self.directory / (name + "-external-sentinel.txt")
                sentinel.write_bytes(b"external inode must remain unchanged")
                os.link(sentinel, destination)
                self.assertTrue(os.path.samefile(sentinel, destination))
                result = self.run_installer(command, target_arg, target, [force_arg])
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertEqual(b"external inode must remain unchanged", sentinel.read_bytes())
                self.assertFalse(os.path.samefile(sentinel, destination))
                self.assertEqual((ROOT / "zcode" / validator.INSTALL_FILES[-1]).read_bytes(), destination.read_bytes())
                self.assertEqual([], list(target.rglob(".loop-engine-install.*")))

    def test_source_target_overlap_rejected(self):
        for name, command, target_arg, force_arg in self.available_installers():
            with self.subTest(installer=name):
                sandbox = self.directory / name / "repository"
                shutil.copytree(ROOT / "scripts", sandbox / "scripts")
                shutil.copytree(ROOT / "zcode", sandbox / "zcode")
                adjusted = [str(sandbox / "scripts" / Path(part).name)
                            if part.endswith(("install.sh", "install.ps1")) else part for part in command]
                original = {p.relative_to(sandbox): p.read_bytes() for p in sandbox.rglob("*") if p.is_file()}
                targets = [sandbox / "zcode", sandbox, sandbox / "zcode" / "nested",
                           sandbox / "zcode" / ".", Path(sandbox.anchor)]
                if os.name == "nt":
                    targets.append(Path(str(sandbox / "zcode").upper()))
                for target in targets:
                    result = self.run_installer(adjusted, target_arg, target, [force_arg])
                    self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                    self.assertIn("must not overlap", result.stdout + result.stderr)
                self.assertEqual(original, {p.relative_to(sandbox): p.read_bytes() for p in sandbox.rglob("*") if p.is_file()})
                self.assertFalse((sandbox / "zcode/nested").exists())

    def test_symlink_destination_rejected_when_supported(self):
        supported = False
        for name, command, target_arg, force_arg in self.available_installers():
            with self.subTest(installer=name):
                target = self.directory / name
                destination = target / validator.INSTALL_FILES[-1]
                destination.parent.mkdir(parents=True)
                sentinel = self.directory / (name + "-sentinel.txt")
                sentinel.write_text("unchanged", encoding="utf-8")
                try:
                    destination.symlink_to(sentinel)
                except (OSError, NotImplementedError):
                    continue
                supported = True
                result = self.run_installer(command, target_arg, target, [force_arg])
                self.assertNotEqual(0, result.returncode)
                self.assertEqual("unchanged", sentinel.read_text(encoding="utf-8"))
                self.assertFalse((target / "agents").exists())
        if not supported:
            self.skipTest("File symlink creation is unavailable on this host")

    def test_symlink_parent_is_rejected_when_supported(self):
        supported = False
        for name, command, target_arg, force_arg in self.available_installers():
            with self.subTest(installer=name):
                target = self.directory / name
                target.mkdir()
                outside = self.directory / (name + "-separate")
                outside.mkdir()
                try:
                    (target / "agents").symlink_to(outside, target_is_directory=True)
                except (OSError, NotImplementedError):
                    continue
                supported = True
                result = self.run_installer(command, target_arg, target, [force_arg])
                self.assertNotEqual(0, result.returncode)
                self.assertEqual([], list(outside.iterdir()))
                self.assertFalse((target / "commands").exists())
        if not supported:
            self.skipTest("Directory symlink creation is unavailable on this host")


if __name__ == "__main__":
    unittest.main()
