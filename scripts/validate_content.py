#!/usr/bin/env python3
"""Validate this repository's publishable configuration using only the stdlib.

This is a bounded JSON Schema subset, not a general-purpose schema validator.
Every distributed text file is scanned, including this module and test sources.
Forbidden pattern definitions and fixtures are composed without raw secrets.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROLES = ("code-writer", "code-reviewer", "code-generate-test", "discriminator")
TARGETS = ROLES[:3] + ("user",)
VERDICTS = ("pass", "retry", "human_review_required", "fail")
FINAL_STATUSES = ("pass", "human_review_required", "fail", "max_iterations_reached")
STAGES = ("INIT", "WRITE", "REVIEW", "TEST_GENERATE", "TEST_RUN", "DISCRIMINATE")
SCHEMA_FIELDS = {
    "writer": ("changed_files", "implementation_summary", "behavior_changes",
               "risk_notes", "test_recommendations", "needs_review"),
    "reviewer": ("verdict", "risk_assessment", "blocking_findings",
                 "non_blocking_findings", "missed_tests", "review_confidence"),
    "test-generator": ("test_strategy", "tests_added_or_modified", "coverage_notes",
                       "not_covered", "test_commands", "qa_scenarios"),
    "discriminator": ("overall_status", "writer_score", "reviewer_score",
                      "test_generator_score", "discriminator_confidence",
                      "blocking_issues", "next_action", "evidence_summary",
                      "policy_exceptions", "memory_proposals",
                      "memory_not_proposed_reason", "reasoning_summary"),
}
AGENT_SCHEMAS = dict(zip(ROLES, SCHEMA_FIELDS))
INSTALL_FILES = tuple("agents/" + role + ".md" for role in ROLES) + (
    "commands/loop-engine.md", "skills/loop-engine/SKILL.md")
REQUIRED_FILES = (
    "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", ".gitignore",
    "zcode/AGENTS.example.md", "docs/architecture.md", "docs/installation.md",
    "docs/customization.md", "docs/memory-policy.md", "docs/privacy.md",
    "examples/basic-flow.md", "examples/retry-reviewer.md",
    "examples/tests-not-run.md", "examples/human-review-required.md",
    "scripts/install.ps1", "scripts/install.sh", "scripts/validate_content.py",
    "tests/test_validate_content.py", ".github/workflows/validate.yml",
) + tuple("zcode/" + path for path in INSTALL_FILES) + tuple(
    "zcode/loop/memory/" + role + ".example.md" for role in ROLES
) + tuple("schemas/" + name + "-output.schema.json" for name in SCHEMA_FIELDS)

# Deliberately describe forbidden patterns without embedding real private data.
FORBIDDEN = (
    ("absolute local path", re.compile(r"(?i)\b[A-Z]:[\\/]|(?<!\w)/(?:home|Users|private|tmp|var|opt|mnt)/")),
    ("private account or organization", re.compile(
        "|".join(("Admin" + "istrator", "east" + "-money")), re.I)),
    ("model UUID", re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.I)),
    ("credential", re.compile(
        r"-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
        r"sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16})\b|"
        r"(?i:(?:api[_-]?key|password|access[_-]?token)\s*[:=]\s*[\"']?[^\s\"']{8,})")),
    ("runtime record", re.compile(
        r"\b(?:sess_[A-Za-z0-9._-]+|session[_-]id\s*[:=]|"
        r"rollout[_-]id\s*[:=]|transcript[_-]id\s*[:=])", re.I)),
    ("unfinished placeholder", re.compile(r"\b(?:TO" + r"DO|FIX" + r"ME)\b|<[^>]*(?:username|repo-url|email)[^>]*>", re.I)),
)
TYPE_NAMES = {"object", "array", "string", "number", "integer", "boolean", "null"}
SCHEMA_KEYWORDS = {
    "$schema", "$ref", "$defs", "title", "description", "type", "required",
    "properties", "additionalProperties", "items", "enum", "const", "minimum",
    "maximum", "minLength", "minItems", "maxItems", "allOf", "anyOf", "if", "then",
}


def read_text(path):
    return path.read_text(encoding="utf-8-sig")


def load_json(text):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("non-finite JSON constant: " + value)

    return json.loads(text, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("unclosed frontmatter") from exc
    result = {}
    for line in lines[1:end]:
        match = re.fullmatch(r"([A-Za-z][\w-]*):\s*(.+)", line)
        if not match or match[1] in result:
            raise ValueError("invalid or duplicate frontmatter field")
        result[match[1]] = match[2].strip().strip("\"'")
    return result


def markdown_parts(text):
    """Return prose and fenced blocks; support backtick and tilde fences."""
    prose, blocks, buffer = [], [], []
    opening = None
    for line in text.splitlines():
        if opening is None:
            match = re.match(r"^ {0,3}(`{3,}|~{3,})([^\n]*)$", line)
            if match:
                opening = (match[1][0], len(match[1]), match[2].strip())
                buffer = []
            else:
                prose.append(line)
        elif re.fullmatch(r" {0,3}" + re.escape(opening[0]) +
                          "{" + str(opening[1]) + r",}\s*", line):
            blocks.append((opening[2], "\n".join(buffer)))
            opening = None
        else:
            buffer.append(line)
    if opening is not None:
        raise ValueError("unclosed code fence")
    return "\n".join(prose), blocks


def heading_ids(text):
    ids = set()
    duplicates = {}
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            slug = re.sub(r"[^\w\- ]", "", match[1].lower()).replace(" ", "-")
            count = duplicates.get(slug, 0)
            duplicates[slug] = count + 1
            ids.add(slug if count == 0 else slug + "-" + str(count))
    return ids


def check_links(root, path, prose):
    errors = []
    targets = re.findall(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", prose)
    references = dict(re.findall(r"(?m)^ {0,3}\[([^\]]+)\]:\s*(\S+)", prose))
    targets.extend(references.values())
    for label, reference in re.findall(r"!?\[([^\]]+)\]\[([^\]]*)\]", prose):
        if (reference or label) not in references:
            errors.append("missing Markdown link reference: " + (reference or label))
    for target in targets:
        target = target.strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme in {"https", "http", "mailto"}:
            continue
        if parsed.scheme or parsed.netloc or target.startswith(("/", "\\")):
            errors.append("link must be repository relative: " + target)
            continue
        linked = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
        if not linked.is_relative_to(root):
            errors.append("link escapes repository: " + target)
        elif not linked.exists():
            errors.append("broken relative Markdown link: " + target)
        elif parsed.fragment and linked.is_file() and linked.suffix == ".md":
            if unquote(parsed.fragment) not in heading_ids(read_text(linked)):
                errors.append("missing Markdown anchor: " + target)
    return errors


def resolve_ref(schema, ref):
    if not isinstance(ref, str) or not ref.startswith("#/"):
        raise ValueError("only local schema references are supported")
    node = schema
    for segment in ref[2:].split("/"):
        node = node[segment.replace("~1", "/").replace("~0", "~")]
    return node


def check_schema_node(node, root, location="$", active_refs=()):
    if not isinstance(node, dict):
        raise ValueError(location + ": schema must be an object")
    unknown = set(node) - SCHEMA_KEYWORDS
    if unknown:
        raise ValueError(location + ": unsupported schema keywords " + str(sorted(unknown)))
    if "$ref" in node:
        ref = node["$ref"]
        if ref in active_refs:
            raise ValueError(location + ": cyclic schema reference")
        try:
            resolved = resolve_ref(root, ref)
        except (KeyError, TypeError) as exc:
            raise ValueError(location + ": broken schema reference") from exc
        check_schema_node(resolved, root, location + ".$ref", active_refs + (ref,))
    if "type" in node:
        types = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not types or any(not isinstance(t, str) or t not in TYPE_NAMES for t in types):
            raise ValueError(location + ": invalid schema type")
    properties = node.get("properties", {})
    if not isinstance(properties, dict):
        raise ValueError(location + ": properties must be an object")
    required = node.get("required", [])
    if not isinstance(required, list) or any(not isinstance(v, str) for v in required):
        raise ValueError(location + ": invalid required fields")
    if len(set(required)) != len(required) or not set(required) <= set(properties):
        raise ValueError(location + ": required fields must have properties")
    if "additionalProperties" in node and not isinstance(node["additionalProperties"], bool):
        raise ValueError(location + ": additionalProperties must be boolean")
    if "enum" in node and (not isinstance(node["enum"], list) or not node["enum"]):
        raise ValueError(location + ": invalid enum")
    for key in ("minimum", "maximum", "minLength", "minItems", "maxItems"):
        if key in node:
            value = node[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(location + ": invalid " + key)
            if key in {"minLength", "minItems", "maxItems"} and (value < 0 or not isinstance(value, int)):
                raise ValueError(location + ": invalid " + key)
    for key, value in properties.items():
        check_schema_node(value, root, location + "." + key, active_refs)
    for key in ("items", "if", "then"):
        if key in node:
            check_schema_node(node[key], root, location + "." + key, active_refs)
    for key in ("allOf", "anyOf"):
        if key in node:
            if not isinstance(node[key], list) or not node[key]:
                raise ValueError(location + ": invalid " + key)
            for child in node[key]:
                check_schema_node(child, root, location + "." + key, active_refs)
    definitions = node.get("$defs", {})
    if not isinstance(definitions, dict):
        raise ValueError(location + ": invalid definitions")
    for key, value in definitions.items():
        check_schema_node(value, root, location + ".$defs." + key, active_refs)


def object_contract(node, fields, location):
    if (node.get("type") != "object" or node.get("additionalProperties") is not False or
            set(node.get("required", [])) != set(fields) or
            set(node.get("properties", {})) != set(fields)):
        raise ValueError(location + ": missing or inconsistent key schema fields")


def nested_contract(node, expected, location):
    object_contract(node, expected, location)
    if node["properties"] != expected:
        raise ValueError(location + ": invalid nested field types, lengths or enums")


def check_schema_contract(name, schema):
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("incorrect JSON Schema dialect")
    check_schema_node(schema, schema)
    object_contract(schema, SCHEMA_FIELDS[name], name)
    props = schema["properties"]
    for key, definition in props.items():
        if definition.get("type") == "array" and "items" not in definition:
            raise ValueError(key + ": array requires items")
    string_arrays = {
        "writer": SCHEMA_FIELDS["writer"][:-1],
        "reviewer": ("missed_tests",),
        "test-generator": SCHEMA_FIELDS["test-generator"][:-1],
        "discriminator": ("evidence_summary", "policy_exceptions"),
    }
    for key in string_arrays[name]:
        if (props[key].get("type") != "array" or
                props[key].get("items") != {"type": "string", "minLength": 1}):
            raise ValueError(key + ": expected nonempty string array items")
    if name == "writer" and props["needs_review"] != {"type": "boolean", "const": True}:
        raise ValueError("needs_review must always be true")
    string_field = {"type": "string", "minLength": 1}
    if name == "reviewer":
        if props["verdict"] != {"type": "string", "enum": ["approve", "request_changes"]}:
            raise ValueError("invalid reviewer verdict enum")
        if props["risk_assessment"] != {"type": "string", "enum": ["low", "medium", "high"]}:
            raise ValueError("invalid risk enum")
        nested_contract(schema["$defs"]["finding"], {
            "file": string_field, "line": {"type": ["integer", "null"], "minimum": 1},
            "severity": {"type": "string", "enum": ["blocker", "major", "minor"]},
            "problem": string_field, "impact": string_field, "suggestion": string_field,
        }, "finding")
        if props["non_blocking_findings"] != {"type": "array", "items": {"$ref": "#/$defs/finding"}}:
            raise ValueError("non_blocking_findings must reference finding objects")
        if not schema.get("allOf"):
            raise ValueError("reviewer blocking condition missing")
        base = {"verdict": "approve", "risk_assessment": "low", "blocking_findings": [],
                "non_blocking_findings": [], "missed_tests": [], "review_confidence": .9}
        finding = {"file": "src/sample.py", "line": 1, "severity": "major", "problem": "Defect",
                   "impact": "Wrong result", "suggestion": "Fix defect"}
        valid = [base, dict(base, verdict="request_changes", blocking_findings=[finding])]
        invalid = [dict(base, blocking_findings=[finding]),
                   dict(base, verdict="request_changes", blocking_findings=[dict(finding, severity="minor")])]
        if any(validate_instance(value, schema) for value in valid) or any(
                not validate_instance(value, schema) for value in invalid):
            raise ValueError("reviewer blocking conditions do not enforce verdict and severity")
    if name == "test-generator":
        nested_contract(schema["$defs"]["scenario"], {
            "scenario": string_field,
            "steps": {"type": "array", "minItems": 1, "items": string_field},
            "expected_result": string_field,
            "priority": {"type": "string", "enum": ["P0", "P1", "P2"]},
        }, "scenario")
        if props["qa_scenarios"] != {"type": "array", "items": {"$ref": "#/$defs/scenario"}}:
            raise ValueError("qa_scenarios must reference scenario objects")
    score_fields = ("review_confidence",) if name == "reviewer" else ()
    if name == "discriminator":
        if props["overall_status"].get("enum") != list(VERDICTS):
            raise ValueError("invalid iteration verdict enum")
        score_fields = ("writer_score", "reviewer_score", "test_generator_score", "discriminator_confidence")
        definitions = schema["$defs"]
        nested_contract(definitions["issue"], {
            "owner": {"type": "string", "enum": list(TARGETS)},
            "issue": string_field, "required_action": string_field,
        }, "blocking_issues")
        nested_contract(definitions["action"], {
            "target_agent": {"type": "string", "enum": list(TARGETS)}, "instruction": string_field,
        }, "next_action")
        nested_contract(definitions["proposal"], {
            "principle": string_field, "reason": string_field, "evidence": string_field,
        }, "proposal")
        if props["blocking_issues"].get("items") != {"$ref": "#/$defs/issue"}:
            raise ValueError("blocking_issues must reference issue objects")
        object_contract(props["memory_proposals"], ROLES, "memory_proposals")
        for role in ROLES:
            if props["memory_proposals"]["properties"][role] != {
                    "type": "array", "items": {"$ref": "#/$defs/proposal"}}:
                raise ValueError("Memory group must contain proposal objects")
        if len(schema.get("allOf", [])) < 4:
            raise ValueError("discriminator status condition missing")
        # Probe conditional semantics, rather than accepting an allOf list by length.
        base = {
            "overall_status": "pass", "writer_score": .9, "reviewer_score": .9,
            "test_generator_score": .9, "discriminator_confidence": .9,
            "blocking_issues": [], "next_action": None, "evidence_summary": ["Synthetic evidence"],
            "policy_exceptions": [], "memory_proposals": {role: [] for role in ROLES},
            "memory_not_proposed_reason": "Synthetic probe", "reasoning_summary": "Synthetic decision",
        }
        action = {"target_agent": "code-writer", "instruction": "Check evidence"}
        user_action = {"target_agent": "user", "instruction": "Resolve requirement"}
        valid = [base, dict(base, overall_status="fail"),
                 dict(base, overall_status="retry", next_action=action),
                 dict(base, overall_status="human_review_required", next_action=user_action)]
        invalid = [dict(base, next_action=action), dict(base, overall_status="fail", next_action=action),
                   dict(base, overall_status="retry"), dict(base, overall_status="human_review_required"),
                   dict(base, overall_status="human_review_required", next_action=action),
                   dict(base, blocking_issues=[{"owner": "code-writer", "issue": "Defect",
                                               "required_action": "Fix defect"}])]
        if any(validate_instance(value, schema) for value in valid) or any(
                not validate_instance(value, schema) for value in invalid):
            raise ValueError("discriminator status conditions do not enforce action and blocking rules")
    for key in score_fields:
        if props[key] != {"type": "number", "minimum": 0, "maximum": 1}:
            raise ValueError(key + ": score must range from 0 to 1")


def validate_instance(value, node, schema=None, location="$"):
    """Validate precisely the keywords accepted by check_schema_node."""
    schema = node if schema is None else schema
    errors = []
    if "$ref" in node:
        errors.extend(validate_instance(value, resolve_ref(schema, node["$ref"]), schema, location))
    type_checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v),
    }
    if "type" in node:
        types = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not any(type_checks[t](value) for t in types):
            return errors + [location + ": incorrect type"]
    if "enum" in node and value not in node["enum"]:
        errors.append(location + ": value not in enum")
    if "const" in node and (value != node["const"] or type(value) is not type(node["const"])):
        errors.append(location + ": incorrect const")
    if isinstance(value, dict):
        for field in node.get("required", []):
            if field not in value:
                errors.append(location + ": missing " + field)
        properties = node.get("properties", {})
        if node.get("additionalProperties") is False and set(value) - set(properties):
            errors.append(location + ": unexpected fields")
        for field in set(value) & set(properties):
            errors.extend(validate_instance(value[field], properties[field], schema, location + "." + field))
    if isinstance(value, list):
        if len(value) < node.get("minItems", 0) or len(value) > node.get("maxItems", math.inf):
            errors.append(location + ": invalid array length")
        if "items" in node:
            for index, item in enumerate(value):
                errors.extend(validate_instance(item, node["items"], schema, location + "[" + str(index) + "]"))
    if isinstance(value, str) and len(value) < node.get("minLength", 0):
        errors.append(location + ": string too short")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < node.get("minimum", -math.inf) or value > node.get("maximum", math.inf):
            errors.append(location + ": number out of range")
    for child in node.get("allOf", []):
        errors.extend(validate_instance(value, child, schema, location))
    if "anyOf" in node and all(validate_instance(value, child, schema, location) for child in node["anyOf"]):
        errors.append(location + ": no anyOf branch matches")
    if "if" in node and not validate_instance(value, node["if"], schema, location):
        errors.extend(validate_instance(value, node.get("then", {}), schema, location))
    return errors


def final_status(verdict, target, iteration):
    if verdict not in VERDICTS or not isinstance(iteration, int) or isinstance(iteration, bool) or not 1 <= iteration <= 3:
        raise ValueError("invalid verdict or iteration")
    if verdict == "human_review_required" or (verdict == "retry" and target == "user"):
        return "human_review_required"
    if verdict in {"pass", "fail"}:
        return verdict
    if target not in TARGETS:
        raise ValueError("invalid retry target")
    return "max_iterations_reached" if iteration == 3 else None


def check_discriminator_policy(output):
    errors = []
    proposals = output["memory_proposals"]
    has_proposals = any(proposals.values())
    if has_proposals != (output["memory_not_proposed_reason"] is None):
        errors.append("Memory proposal reason is inconsistent")
    if output["overall_status"] == "retry" and output["blocking_issues"]:
        owners = {issue["owner"] for issue in output["blocking_issues"]}
        if output["next_action"]["target_agent"] not in owners:
            errors.append("retry target must match a blocking issue owner")
    if output["overall_status"] == "pass":
        thresholds = {"writer_score": .75, "reviewer_score": .75,
                      "test_generator_score": .70, "discriminator_confidence": .75}
        if any(output[key] < minimum for key, minimum in thresholds.items()) and not output["policy_exceptions"]:
            errors.append("below-threshold pass needs recorded policy_exceptions")
    return errors


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def check_test_run(run):
    required = {"status", "commands", "exit_codes", "summary", "reason"}
    if not isinstance(run, dict) or set(run) != required:
        return ["invalid TEST_RUN evidence fields"]
    if (run["status"] not in {"passed", "failed", "tests_not_run"} or
            not isinstance(run["commands"], list) or not isinstance(run["exit_codes"], list) or
            len(run["commands"]) != len(run["exit_codes"]) or
            any(not nonempty_string(v) for v in run["commands"]) or
            any(not isinstance(v, int) or isinstance(v, bool) for v in run["exit_codes"]) or
            not nonempty_string(run["summary"]) or
            (run["reason"] is not None and not nonempty_string(run["reason"]))):
        return ["invalid TEST_RUN evidence values"]
    if run["status"] == "tests_not_run":
        if run["commands"] or run["exit_codes"] or not nonempty_string(run["reason"]):
            return ["tests_not_run requires empty commands/exits and explicit reason"]
    elif run["status"] == "passed":
        if not run["commands"] or any(run["exit_codes"]):
            return ["passed requires successful executed commands"]
    elif not run["commands"] or not any(run["exit_codes"]) or not nonempty_string(run["reason"]):
        return ["failed requires executed commands, nonzero exit and explicit reason"]
    return []


def check_json_block(data, path, schemas):
    errors = []
    if path.parent.name == "agents":
        name = AGENT_SCHEMAS.get(path.stem)
        if name in schemas:
            errors.extend(validate_instance(data, schemas[name]))
            if name == "discriminator" and not errors:
                errors.extend(check_discriminator_policy(data))
        return errors
    if "examples" not in path.parts:
        return errors
    if not isinstance(data, dict):
        return ["example envelope must be an object"]
    required = {"iteration", "final_status", "writer_output", "reviewer_output",
                "test_generator_output", "test_run", "discriminator_output"}
    if set(data) != required:
        return ["example envelope missing required fields or has unexpected fields: " +
                ", ".join(sorted(required - set(data)))]
    for field, name in (("writer_output", "writer"), ("reviewer_output", "reviewer"),
                        ("test_generator_output", "test-generator"), ("discriminator_output", "discriminator")):
        if name not in schemas:
            continue
        current = validate_instance(data[field], schemas[name], location=field)
        errors.extend(current)
        if name == "discriminator" and not current:
            errors.extend(check_discriminator_policy(data[field]))
            action = data[field]["next_action"]
            target = action["target_agent"] if action else None
            try:
                expected = final_status(data[field]["overall_status"], target, data["iteration"])
                if data["final_status"] != expected:
                    errors.append("inconsistent workflow final_status")
            except ValueError as exc:
                errors.append(str(exc))
    if data["final_status"] is not None and data["final_status"] not in FINAL_STATUSES:
        errors.append("invalid workflow final status")
    errors.extend(check_test_run(data["test_run"]))
    return errors


def check_protocol(path, text):
    errors = []
    for token in ROLES + STAGES + VERDICTS + FINAL_STATUSES + ("三轮",):
        if token not in text:
            errors.append("missing required role/stage/status: " + token)
    transitions = (
        "retry target=code-writer -> WRITE -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE",
        "retry target=code-reviewer -> REVIEW -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE",
        "retry target=code-generate-test -> TEST_GENERATE -> TEST_RUN -> DISCRIMINATE",
        "retry target=user -> human_review_required",
    )
    for transition in transitions:
        if transition not in text:
            errors.append("missing or misspelled retry transition: " + transition)
    for name, fields in SCHEMA_FIELDS.items():
        for field in fields:
            if field not in text:
                errors.append("missing output contract field: " + name + "." + field)
    if path.name == "SKILL.md":
        for heading in ("## 定位与能力边界", "## 角色", "## 前置检查 INIT", "## 阶段",
                        "## 默认评分政策", "## Retry 状态转移", "## 判停与最终状态",
                        "## Memory approval", "## 最终报告"):
            if heading not in text:
                errors.append("missing required section: " + heading)
    for key, threshold in (("writer_score", "0.75"), ("reviewer_score", "0.75"),
                           ("test_generator_score", "0.70"), ("discriminator_confidence", "0.75")):
        if key + " >= " + threshold not in text:
            errors.append("missing default score policy: " + key)
    return errors


def memory_template(role):
    return (
        "# " + role + " Memory 空模板\n\n"
        "此文件不含经验，不自动安装或加载。下列章节为空，只有审批后才可填入经验证的原则。\n\n"
        "## 已批准原则\n\n## 证据与适用范围\n\n## 用户确认\n\n"
        "discriminator 仅 proposal；主会话展示建议，用户明确确认后才写入。"
        "未确认不写，不记录一次性任务或私有信息。\n"
    )


def check_memory_approval(text):
    patterns = (r"discriminator\s*仅\s*proposal", r"主会话展示", r"用户明确确认[^\n。；]*后才写入")
    return all(re.search(pattern, text) for pattern in patterns)


def validate(root):
    root = Path(root).resolve()
    if not root.is_dir():
        return ["repository root is not a directory"]
    errors, texts, schemas = [], {}, {}
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(relative + ": missing required file or unsafe symlink")
    # Scan every publishable text, including extra documentation, not just required files.
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        if any(part in {"__pycache__"} for part in parts) or path.suffix.lower() == ".pyc":
            errors.append(relative + ": forbidden Python bytecode cache")
            continue
        if any(part.startswith(".validation-") or part == ".git" for part in parts):
            continue
        forbidden_directories = {"cli", "v2", "plans", "artifacts", "exec", "rollout", "rollouts",
                                 "logs", "transcripts", "sessions"}
        if any(part in forbidden_directories for part in parts):
            errors.append(relative + ": forbidden runtime directory content")
            continue
        if path.is_symlink():
            errors.append(relative + ": published symlink is not allowed")
            continue
        if not path.is_file():
            continue
        if path.suffix in {".jsonl", ".log", ".db", ".sqlite", ".sqlite3", ".key", ".pem"}:
            errors.append(relative + ": forbidden runtime or credential file")
            continue
        try:
            text = read_text(path)
        except (OSError, UnicodeError) as exc:
            errors.append(relative + ": not readable UTF-8 text: " + type(exc).__name__)
            continue
        texts[relative] = text
        for label, pattern in FORBIDDEN:
            if pattern.search(text):
                errors.append(relative + ": forbidden " + label)
    for name in SCHEMA_FIELDS:
        relative = "schemas/" + name + "-output.schema.json"
        if relative in texts:
            try:
                schema = load_json(texts[relative])
                check_schema_contract(name, schema)
                schemas[name] = schema
            except (ValueError, KeyError, TypeError, RecursionError) as exc:
                errors.append(relative + ": invalid JSON schema: " + str(exc))
    for relative, text in texts.items():
        path = root / relative
        if path.suffix == ".json" and not relative.startswith("schemas/"):
            try:
                load_json(text)
            except ValueError as exc:
                errors.append(relative + ": invalid JSON: " + str(exc))
        if path.suffix != ".md":
            continue
        try:
            prose, blocks = markdown_parts(text)
            errors.extend(relative + ": " + error for error in check_links(root, path, prose))
            for language, body in blocks:
                if language == "json":
                    try:
                        data = load_json(body)
                        errors.extend(relative + ": " + error for error in check_json_block(data, path, schemas))
                    except (ValueError, KeyError, TypeError) as exc:
                        errors.append(relative + ": invalid JSON example: " + str(exc))
        except ValueError as exc:
            errors.append(relative + ": " + str(exc))
        if relative in {"zcode/skills/loop-engine/SKILL.md", "zcode/commands/loop-engine.md"}:
            errors.extend(relative + ": " + error for error in check_protocol(path, text))
        if relative.startswith("zcode/") or relative == "docs/memory-policy.md":
            if not check_memory_approval(text):
                errors.append(relative + ": missing Memory approval rule (proposal, main session, explicit confirmation)")
        if relative.startswith("zcode/agents/") or relative == "zcode/skills/loop-engine/SKILL.md":
            try:
                metadata = frontmatter(text)
                expected = path.stem if path.parent.name == "agents" else "loop-engine"
                if set(metadata) != {"name", "description"} or metadata.get("name") != expected or not metadata.get("description"):
                    raise ValueError("frontmatter requires matching name and nonempty description only")
            except ValueError as exc:
                errors.append(relative + ": " + str(exc))
        if relative.startswith("zcode/loop/memory/"):
            role = path.name.removesuffix(".example.md")
            if role not in ROLES or text != memory_template(role):
                errors.append(relative + ": Memory must match the exact empty template")
    readme = texts.get("README.md", "")
    for heading in ("## 定位与亮点", "## 状态机", "## 快速开始", "## 安装", "## 使用",
                    "## 项目结构", "## 验证方式", "## 能力边界", "## 隐私安全", "## License"):
        if heading not in readme:
            errors.append("README.md: missing required section " + heading)
    license_text = texts.get("LICENSE", "")
    if "MIT License" not in license_text or "Copyright (c) 2026 Loop Engine Contributors" not in license_text:
        errors.append("LICENSE: incorrect license or copyright")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Repository root; defaults to the script's repository")
    args = parser.parse_args(argv)
    errors = validate(args.root)
    if errors:
        for error in errors:
            print("ERROR: " + error, file=sys.stderr)
        print("Content validation failed: " + str(len(errors)) + " issue(s).", file=sys.stderr)
        return 1
    print("Content validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
