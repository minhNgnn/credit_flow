"""Static check: each agent file imports call_tool (proves the wiring landed
and won't drift back to direct .ainvoke calls). Also asserts no
`tools["..."].ainvoke(` call sites remain — prevents regression.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _imports_call_tool(path: Path) -> bool:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "app.agents.common":
            for alias in node.names:
                if alias.name == "call_tool":
                    return True
    return False


def test_financial_imports_call_tool():
    assert _imports_call_tool(_REPO / "worker/app/agents/financial.py")


def test_policy_imports_call_tool():
    assert _imports_call_tool(_REPO / "worker/app/agents/policy.py")


def test_collateral_imports_call_tool():
    assert _imports_call_tool(_REPO / "worker/app/agents/collateral.py")


def test_customer360_imports_call_tool():
    assert _imports_call_tool(_REPO / "worker/app/agents/customer360.py")


def test_no_direct_ainvoke_in_agents():
    """Regression guard: no `tools[\"name\"].ainvoke(` call sites left in
    the agent files — they must go through call_tool()."""
    pat = re.compile(r'tools\["[a-zA-Z_][a-zA-Z0-9_]+"\]\.ainvoke\(')
    for name in ("financial", "policy", "collateral", "customer360"):
        src = (_REPO / f"worker/app/agents/{name}.py").read_text()
        assert not pat.search(src), f"direct .ainvoke still present in {name}.py"