"""BONCML 统计分析引擎核心包"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# 确保插件目录在 Python 路径中
_PLUGIN_DIR = str(Path(__file__).resolve().parent.parent)
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

# 导出核心功能
from ._core import (
    TOOLSET,
    _finalize_error,
    _finalize_success,
    _normalize_args_for_algo,
    _validate_columns,
    _run_algo_directly,
    _classify_runtime_exception,
    _read_header_only,
    _get_runtime_root,
    _get_python_path,
    _COLUMN_ARG_SPEC,
    _has_vendored_algos,
    _get_lib_path,
    _prepare_vendored_runtime,
    _resolve_python_api_root,
)

from ._registry import (
    get_catalog,
    get_algo_map,
    get_tool_budgets,
)

from ._schemas import (
    _build_tool_docs_from_schemas,
    _build_reranker_docs_from_schemas,
    PROPOSE_PLAN_SCHEMA,
)

from ._plan import _make_plan_handler

__version__ = "0.3.0"