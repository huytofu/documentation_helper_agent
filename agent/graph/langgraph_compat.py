"""Compatibility shims for langgraph versions vs pinned CopilotKit.

CopilotKit 0.1.44 imports ``langgraph.graph.graph.CompiledGraph``, which was
removed/moved in langgraph >= 0.5. Provide an alias module when missing.
"""

from __future__ import annotations

import sys
import types


def ensure_compiled_graph_alias() -> None:
    if "langgraph.graph.graph" in sys.modules:
        return
    try:
        import langgraph.graph.graph  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    from langgraph.graph.state import CompiledStateGraph

    mod = types.ModuleType("langgraph.graph.graph")
    mod.CompiledGraph = CompiledStateGraph
    mod.CompiledStateGraph = CompiledStateGraph
    sys.modules["langgraph.graph.graph"] = mod
