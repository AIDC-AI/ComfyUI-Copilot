#!/usr/bin/env python3
"""
Validate ComfyUI-Copilot training dataset quality.

Checks every conversation for:
  1. Structural validity (correct message format, roles)
  2. Tool call format (valid JSON arguments, known tool names)
  3. Workflow JSON validity (proper node structure, valid connections)
  4. Logical tool ordering (plan first, save before validate, etc.)
  5. No orphaned tool results (every tool result has a matching call)
  6. Token budget estimation (flag conversations that are too long/short)

Usage:
    python validate_dataset.py training_data.jsonl
    python validate_dataset.py training_data.jsonl --strict --fix-output fixed.jsonl

Enhanced by Claude Opus 4.6
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tool_schemas import ALL_TOOLS, CURRENT_TOOLS

# Known tool names (current + future)
KNOWN_TOOLS = {t["function"]["name"] for t in ALL_TOOLS}

# Required roles in a conversation
REQUIRED_ROLES = {"system", "user", "assistant"}

# Logical ordering rules: tool A should generally come before tool B
ORDERING_RULES = [
    ("plan_tasks", "save_workflow"),
    ("plan_tasks", "search_nodes"),
    ("search_nodes", "save_workflow"),
    ("save_workflow", "validate_workflow"),
    ("validate_workflow", "execute_workflow"),
    ("execute_workflow", "check_execution_result"),
]

# Token limits
MIN_TOKENS_PER_EXAMPLE = 100
MAX_TOKENS_PER_EXAMPLE = 12000
WARN_TOKENS_PER_EXAMPLE = 8000


class ValidationError:
    """Single validation issue."""
    def __init__(self, level: str, code: str, message: str, example_idx: int = -1):
        self.level = level  # "error", "warning", "info"
        self.code = code
        self.message = message
        self.example_idx = example_idx

    def __repr__(self):
        return f"[{self.level.upper()}] Example {self.example_idx}: {self.code} — {self.message}"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def validate_message_structure(messages: list[dict], idx: int) -> list[ValidationError]:
    """Validate basic message list structure."""
    errors = []

    if not messages:
        errors.append(ValidationError("error", "EMPTY_MESSAGES", "No messages", idx))
        return errors

    # Must start with system
    if messages[0].get("role") != "system":
        errors.append(ValidationError("error", "NO_SYSTEM", "First message must be system role", idx))

    # Must have at least one user message
    has_user = any(m.get("role") == "user" for m in messages)
    if not has_user:
        errors.append(ValidationError("error", "NO_USER", "No user message found", idx))

    # Must end with assistant text (not tool call)
    last = messages[-1]
    if last.get("role") != "assistant":
        errors.append(ValidationError("warning", "NO_FINAL_ASSISTANT",
                                       f"Last message role is '{last.get('role')}', expected 'assistant'", idx))
    elif last.get("tool_calls"):
        errors.append(ValidationError("warning", "ENDS_WITH_TOOL_CALL",
                                       "Conversation ends with tool call, not text response", idx))

    # Check all roles are valid
    valid_roles = {"system", "user", "assistant", "tool"}
    for i, msg in enumerate(messages):
        role = msg.get("role")
        if role not in valid_roles:
            errors.append(ValidationError("error", "INVALID_ROLE",
                                           f"Message {i} has invalid role '{role}'", idx))

    return errors


def validate_tool_calls(messages: list[dict], idx: int) -> list[ValidationError]:
    """Validate all tool calls and results."""
    errors = []
    pending_calls = {}  # call_id -> tool_name

    for i, msg in enumerate(messages):
        # Check assistant tool calls
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                # Must have required fields
                if "id" not in tc:
                    errors.append(ValidationError("error", "MISSING_CALL_ID",
                                                   f"Message {i}: tool call missing 'id'", idx))
                    continue

                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "")

                # Check tool name is known
                if name not in KNOWN_TOOLS:
                    errors.append(ValidationError("error", "UNKNOWN_TOOL",
                                                   f"Message {i}: unknown tool '{name}'", idx))

                # Check arguments are valid JSON
                if args_str:
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        if not isinstance(args, dict):
                            errors.append(ValidationError("error", "ARGS_NOT_DICT",
                                                           f"Message {i}: tool '{name}' args not a dict", idx))
                    except json.JSONDecodeError as e:
                        errors.append(ValidationError("error", "INVALID_ARGS_JSON",
                                                       f"Message {i}: tool '{name}' invalid JSON args: {e}", idx))

                pending_calls[tc["id"]] = name

        # Check tool results
        if msg.get("role") == "tool":
            call_id = msg.get("tool_call_id")
            if not call_id:
                errors.append(ValidationError("error", "MISSING_TOOL_CALL_ID",
                                               f"Message {i}: tool result missing 'tool_call_id'", idx))
            elif call_id not in pending_calls:
                errors.append(ValidationError("warning", "ORPHAN_TOOL_RESULT",
                                               f"Message {i}: tool result for unknown call '{call_id}'", idx))
            else:
                del pending_calls[call_id]

            # Content should be valid JSON or string
            content = msg.get("content", "")
            if content:
                try:
                    json.loads(content) if isinstance(content, str) else content
                except json.JSONDecodeError:
                    pass  # String content is fine

    # Check for unresolved tool calls
    for call_id, name in pending_calls.items():
        errors.append(ValidationError("warning", "UNRESOLVED_TOOL_CALL",
                                       f"Tool call '{name}' ({call_id}) never got a result", idx))

    return errors


def validate_workflow_json(messages: list[dict], idx: int) -> list[ValidationError]:
    """Validate workflow JSON passed to save_workflow."""
    errors = []

    for i, msg in enumerate(messages):
        if msg.get("role") != "assistant" or not msg.get("tool_calls"):
            continue

        for tc in msg["tool_calls"]:
            if tc.get("function", {}).get("name") != "save_workflow":
                continue

            args_str = tc["function"].get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                continue  # Already caught by validate_tool_calls

            wf_str = args.get("workflow_json", "")
            if not wf_str:
                errors.append(ValidationError("error", "EMPTY_WORKFLOW",
                                               f"Message {i}: save_workflow has empty workflow_json", idx))
                continue

            try:
                wf = json.loads(wf_str) if isinstance(wf_str, str) else wf_str
            except json.JSONDecodeError as e:
                errors.append(ValidationError("error", "INVALID_WORKFLOW_JSON",
                                               f"Message {i}: workflow_json is invalid JSON: {e}", idx))
                continue

            if not isinstance(wf, dict):
                errors.append(ValidationError("error", "WORKFLOW_NOT_DICT",
                                               f"Message {i}: workflow_json is not a dict", idx))
                continue

            if len(wf) == 0:
                errors.append(ValidationError("error", "EMPTY_WORKFLOW_DICT",
                                               f"Message {i}: workflow_json is empty dict", idx))
                continue

            # Validate each node
            node_ids = set(wf.keys())
            for nid, node in wf.items():
                if not isinstance(node, dict):
                    errors.append(ValidationError("error", "NODE_NOT_DICT",
                                                   f"Message {i}: node '{nid}' is not a dict", idx))
                    continue

                if "class_type" not in node:
                    errors.append(ValidationError("error", "MISSING_CLASS_TYPE",
                                                   f"Message {i}: node '{nid}' missing class_type", idx))

                if "inputs" not in node:
                    errors.append(ValidationError("warning", "MISSING_INPUTS",
                                                   f"Message {i}: node '{nid}' missing inputs", idx))
                    continue

                inputs = node.get("inputs", {})
                if not isinstance(inputs, dict):
                    errors.append(ValidationError("error", "INPUTS_NOT_DICT",
                                                   f"Message {i}: node '{nid}' inputs not a dict", idx))
                    continue

                # Check connections reference valid node IDs
                for field, value in inputs.items():
                    if isinstance(value, list) and len(value) == 2:
                        src_id, src_idx = value
                        if isinstance(src_id, str) and src_id not in node_ids:
                            errors.append(ValidationError("error", "INVALID_CONNECTION",
                                                           f"Message {i}: node '{nid}'.{field} references "
                                                           f"non-existent node '{src_id}'", idx))

    return errors


def validate_tool_ordering(messages: list[dict], idx: int) -> list[ValidationError]:
    """Check that tool calls follow logical ordering."""
    errors = []

    # Extract ordered list of tool call names
    tool_sequence = []
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                name = tc.get("function", {}).get("name", "")
                tool_sequence.append(name)

    # Check ordering rules
    for before, after in ORDERING_RULES:
        before_idx = None
        after_idx = None
        for i, name in enumerate(tool_sequence):
            if name == before and before_idx is None:
                before_idx = i
            if name == after and after_idx is None:
                after_idx = i

        if before_idx is not None and after_idx is not None:
            if after_idx < before_idx:
                errors.append(ValidationError("warning", "TOOL_ORDER",
                                               f"'{after}' called before '{before}' "
                                               f"(positions {after_idx} < {before_idx})", idx))

    return errors


def validate_token_budget(messages: list[dict], idx: int) -> list[ValidationError]:
    """Check token count is reasonable."""
    errors = []

    total_chars = sum(len(json.dumps(m)) for m in messages)
    est_tokens = _estimate_tokens(json.dumps(messages))

    if est_tokens < MIN_TOKENS_PER_EXAMPLE:
        errors.append(ValidationError("warning", "TOO_SHORT",
                                       f"Only ~{est_tokens} tokens (min {MIN_TOKENS_PER_EXAMPLE})", idx))

    if est_tokens > MAX_TOKENS_PER_EXAMPLE:
        errors.append(ValidationError("error", "TOO_LONG",
                                       f"~{est_tokens} tokens exceeds max {MAX_TOKENS_PER_EXAMPLE}", idx))
    elif est_tokens > WARN_TOKENS_PER_EXAMPLE:
        errors.append(ValidationError("warning", "LONG",
                                       f"~{est_tokens} tokens (warn threshold {WARN_TOKENS_PER_EXAMPLE})", idx))

    return errors


def validate_example(example: dict, idx: int) -> list[ValidationError]:
    """Run all validations on a single example."""
    errors = []

    messages = example.get("messages", [])
    if not messages:
        errors.append(ValidationError("error", "NO_MESSAGES", "Example has no messages", idx))
        return errors

    errors.extend(validate_message_structure(messages, idx))
    errors.extend(validate_tool_calls(messages, idx))
    errors.extend(validate_workflow_json(messages, idx))
    errors.extend(validate_tool_ordering(messages, idx))
    errors.extend(validate_token_budget(messages, idx))

    return errors


def validate_dataset(dataset: list[dict], strict: bool = False) -> tuple[bool, list[ValidationError]]:
    """Validate entire dataset.

    Args:
        dataset: List of training examples
        strict: If True, warnings are treated as errors

    Returns:
        (is_valid, list_of_errors)
    """
    all_errors = []

    for i, example in enumerate(dataset):
        errors = validate_example(example, i)
        all_errors.extend(errors)

    error_count = sum(1 for e in all_errors if e.level == "error")
    warning_count = sum(1 for e in all_errors if e.level == "warning")

    if strict:
        is_valid = (error_count + warning_count) == 0
    else:
        is_valid = error_count == 0

    return is_valid, all_errors


def fix_dataset(dataset: list[dict]) -> tuple[list[dict], int]:
    """Remove invalid examples from dataset.

    Returns:
        (fixed_dataset, removed_count)
    """
    fixed = []
    removed = 0

    for i, example in enumerate(dataset):
        errors = validate_example(example, i)
        has_errors = any(e.level == "error" for e in errors)

        if not has_errors:
            fixed.append(example)
        else:
            removed += 1

    return fixed, removed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Validate ComfyUI-Copilot training dataset")
    parser.add_argument("input", help="Input JSONL file to validate")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--fix-output", help="Output fixed JSONL (removes invalid examples)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all issues")
    parser.add_argument("--summary", action="store_true", help="Show only summary")
    parser.add_argument("--max-errors", type=int, default=50, help="Max errors to display")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    # Load dataset
    print(f"Loading {input_path}...")
    dataset = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                dataset.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                sys.exit(1)

    print(f"Loaded {len(dataset)} examples\n")

    # Validate
    is_valid, errors = validate_dataset(dataset, strict=args.strict)

    # Summarize
    from collections import Counter
    error_codes = Counter()
    for e in errors:
        error_codes[f"{e.level}:{e.code}"] += 1

    error_count = sum(1 for e in errors if e.level == "error")
    warning_count = sum(1 for e in errors if e.level == "warning")
    info_count = sum(1 for e in errors if e.level == "info")

    print("=== Validation Results ===")
    print(f"Total examples: {len(dataset)}")
    print(f"Errors: {error_count}")
    print(f"Warnings: {warning_count}")
    print(f"Status: {'PASS ✓' if is_valid else 'FAIL ✗'}")

    if not args.summary:
        if error_codes:
            print("\nIssue breakdown:")
            for code, count in error_codes.most_common():
                print(f"  {code}: {count}")

        if args.verbose and errors:
            print(f"\nDetailed issues (showing up to {args.max_errors}):")
            for e in errors[:args.max_errors]:
                print(f"  {e}")

    # Fix output
    if args.fix_output:
        fixed, removed = fix_dataset(dataset)
        output_path = Path(args.fix_output)
        with open(output_path, "w", encoding="utf-8") as f:
            for example in fixed:
                record = {"messages": example["messages"], "tools": example["tools"]}
                if "metadata" in example:
                    record["metadata"] = example["metadata"]
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"\nFixed dataset: {len(fixed)} examples (removed {removed})")
        print(f"Written to {output_path}")

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
