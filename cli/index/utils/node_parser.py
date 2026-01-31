"""AST-based node definition extraction for ComfyUI packages."""

import ast
import os
import shutil
import subprocess
from pathlib import Path

from .github import extract_github_info


def clone_repo(github_url, dest_dir, timeout=120):
    """Clone a repo to destination directory."""
    try:
        result = subprocess.run(
            ["git", "clone", "--quiet", "--depth=1", github_url, dest_dir],
            capture_output=True,
            timeout=timeout
        )
        return result.returncode == 0
    except Exception:
        return False


def find_python_files(repo_dir):
    """Find all Python files in repo."""
    return list(Path(repo_dir).rglob("*.py"))


def parse_class_attribute(node, attr_name):
    """Extract a class attribute value from AST."""
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == attr_name:
                    return item.value
        elif isinstance(item, ast.AnnAssign):
            if isinstance(item.target, ast.Name) and item.target.id == attr_name:
                return item.value
    return None


def ast_to_value(node):
    """Convert AST node to Python value (simplified)."""
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Tuple):
        return tuple(ast_to_value(el) for el in node.elts)
    if isinstance(node, ast.List):
        return [ast_to_value(el) for el in node.elts]
    if isinstance(node, ast.Dict):
        result = {}
        for k, v in zip(node.keys, node.values):
            key = ast_to_value(k)
            if key:
                result[key] = ast_to_value(v)
        return result
    return None


def extract_input_types(class_node):
    """Extract INPUT_TYPES from a class."""
    inputs = {"required": {}, "optional": {}}

    for item in class_node.body:
        # Check for INPUT_TYPES as classmethod
        if isinstance(item, ast.FunctionDef) and item.name == "INPUT_TYPES":
            for stmt in ast.walk(item):
                if isinstance(stmt, ast.Return) and stmt.value:
                    val = ast_to_value(stmt.value)
                    if isinstance(val, dict):
                        for key in ["required", "optional"]:
                            if key in val and isinstance(val[key], dict):
                                for name, spec in val[key].items():
                                    if isinstance(spec, tuple) and len(spec) > 0:
                                        inputs[key][name] = spec[0]
                                    else:
                                        inputs[key][name] = str(spec)
                        return inputs

        # Check for INPUT_TYPES as class attribute
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "INPUT_TYPES":
                    val = ast_to_value(item.value)
                    if isinstance(val, dict):
                        for key in ["required", "optional"]:
                            if key in val and isinstance(val[key], dict):
                                for name, spec in val[key].items():
                                    if isinstance(spec, tuple) and len(spec) > 0:
                                        inputs[key][name] = spec[0]
                                    else:
                                        inputs[key][name] = str(spec)
                        return inputs

    return inputs


def extract_node_class(class_node):
    """Extract node definition from a class AST node."""
    node_def = {
        "inputs": {"required": {}, "optional": {}},
        "outputs": [],
        "output_names": [],
        "category": ""
    }

    node_def["inputs"] = extract_input_types(class_node)

    return_types = parse_class_attribute(class_node, "RETURN_TYPES")
    if return_types:
        val = ast_to_value(return_types)
        if isinstance(val, (tuple, list)):
            node_def["outputs"] = [str(t) for t in val]

    return_names = parse_class_attribute(class_node, "RETURN_NAMES")
    if return_names:
        val = ast_to_value(return_names)
        if isinstance(val, (tuple, list)):
            node_def["output_names"] = [str(n) for n in val]

    category = parse_class_attribute(class_node, "CATEGORY")
    if category:
        val = ast_to_value(category)
        if val:
            node_def["category"] = str(val)

    return node_def


def find_node_mappings(repo_dir):
    """Find NODE_CLASS_MAPPINGS in repo and extract node definitions."""
    nodes = {}
    class_defs = {}

    # First pass: collect all class definitions
    for py_file in find_python_files(repo_dir):
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_defs[node.name] = node
        except Exception:
            continue

    # Second pass: find NODE_CLASS_MAPPINGS
    for py_file in find_python_files(repo_dir):
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            if "NODE_CLASS_MAPPINGS" not in content:
                continue

            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "NODE_CLASS_MAPPINGS":
                            if isinstance(node.value, ast.Dict):
                                for k, v in zip(node.value.keys, node.value.values):
                                    node_name = ast_to_value(k)
                                    if node_name:
                                        class_name = None
                                        if isinstance(v, ast.Name):
                                            class_name = v.id
                                        elif isinstance(v, ast.Attribute):
                                            class_name = v.attr

                                        if class_name and class_name in class_defs:
                                            node_def = extract_node_class(class_defs[class_name])
                                            nodes[node_name] = node_def
                                        else:
                                            nodes[node_name] = {
                                                "inputs": {"required": {}, "optional": {}},
                                                "outputs": [],
                                                "output_names": [],
                                                "category": ""
                                            }
        except Exception:
            continue

    return nodes


def extract_repo_nodes(row, clone_dir):
    """Clone a repo and extract node definitions."""
    github_url = row["github_url"]
    owner, repo = extract_github_info(github_url)

    if not owner or not repo:
        return github_url, {}

    repo_dir = os.path.join(clone_dir, f"{owner}_{repo}")

    try:
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)

        if not clone_repo(github_url, repo_dir):
            return github_url, {}

        nodes = find_node_mappings(repo_dir)
        return github_url, nodes

    except Exception:
        return github_url, {}

    finally:
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
