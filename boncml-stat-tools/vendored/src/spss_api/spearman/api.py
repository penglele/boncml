#!/usr/bin/env python3
"""SPEARMAN Python API (Spearman ρ / Kendall τ_b 等级相关分析).

对应 SPSS 命令: NONPAR CORR（部分）/ CORRELATIONS（在双变量对话框勾选 Spearman / Kendall）
路径: 分析 > 相关 > 双变量 > 斯皮尔曼、肯德尔

Fortran 入口:
    subroutine compute_spearman_kendall(data, corr_type, use_pairwise,
                                        use_two_tails, corr, pval, counts)

corr_type 取值:
    CORR_SPEARMAN = 2  → Spearman ρ
    CORR_KENDALL  = 1  → Kendall tau_b

输出表（参照 SPSS Nonparametric Correlations 输出面板）:
    - correlations              相关系数矩阵（含对角线 1.000）
    - significance_two_tailed   显著性（双尾 p 值）矩阵
    - n_pairs                   每变量的样本数
    - coefficient_type          "Spearman" | "Kendall"

注意:
    - Fortran 简化实现，counts 为 1D（每变量样本数）
    - Kendall 输出为 tau_b 形式
"""
import importlib
import os
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

here = os.path.abspath(os.path.dirname(__file__))
lib_dir = os.path.normpath(os.path.join(here, '..', '..', '..', 'lib'))
src_dir = os.path.normpath(os.path.join(here, '..', '..'))
for path in (lib_dir, src_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

_algo = importlib.import_module('spearman')

# 与 Fortran 内部常量保持一致（来自 .pyf）
_CORR_KENDALL = 1
_CORR_SPEARMAN = 2

_COEFF_MAP = {
    'spearman': _CORR_SPEARMAN,
    'rho': _CORR_SPEARMAN,
    'kendall': _CORR_KENDALL,
    'tau': _CORR_KENDALL,
    'tau_b': _CORR_KENDALL,
}


def _as_fortran_2d(data: Any) -> np.ndarray:
    """转 (n_obs, n_vars) 二维 float64 Fortran 顺序数组；NaN→-1e308 兜底."""
    if isinstance(data, pd.DataFrame):
        arr = data.to_numpy(dtype=np.float64)
    elif isinstance(data, pd.Series):
        arr = data.to_numpy(dtype=np.float64).reshape(-1, 1)
    else:
        arr = np.asarray(data, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError('data 必须是二维数组 (n_obs, n_vars) 或 DataFrame')
    arr = np.where(np.isnan(arr), -1.0e308, arr)
    return np.asfortranarray(arr)


def _resolve_columns(data: Any, columns: Optional[List[str]]) -> Optional[List[str]]:
    if columns is not None:
        if not columns:
            raise ValueError('columns 不能为空')
        return list(columns)
    if isinstance(data, pd.DataFrame):
        return [str(c) for c in data.columns]
    return None


def _clean_scalar(value: Any) -> Optional[float]:
    val = float(value)
    if not np.isfinite(val) or val <= -1.0e35:
        return None
    return val


def run_spearman(
    data: Any,
    columns: Optional[List[str]] = None,
    coefficient: str = 'spearman',
    use_two_tails: bool = True,
    use_pairwise: bool = False,
    missing: str = 'LISTWISE',
) -> Dict[str, Any]:
    """计算 Spearman ρ 或 Kendall tau_b 等级相关矩阵。

    参数:
        data          : (n_obs, n_vars) 二维数据，支持 numpy / list / DataFrame
        columns       : 变量名列表（可选，DataFrame 可省略）
        coefficient   : 'spearman'（默认）或 'kendall'。别名：'rho'、'tau'、'tau_b'
        use_two_tails : True=双尾（默认），False=单尾
        use_pairwise  : True=逐对（当前实现未生效，listwise 模式）
        missing       : 'LISTWISE' 或 'PAIRWISE'

    返回:
        dict，含 correlations / significance_two_tailed / n_pairs /
        coefficient_type / meta 五个字段。
    """
    coeff_key = (coefficient or 'spearman').lower()
    if coeff_key not in _COEFF_MAP:
        raise ValueError(
            f"coefficient 仅支持 'spearman' 或 'kendall'，当前: {coefficient!r}"
        )
    corr_type = _COEFF_MAP[coeff_key]
    coeff_label = 'Spearman' if corr_type == _CORR_SPEARMAN else 'Kendall'

    missing = (missing or 'LISTWISE').upper()
    if missing not in ('LISTWISE', 'PAIRWISE'):
        raise ValueError(f"missing 仅支持 'LISTWISE' / 'PAIRWISE'，当前: {missing}")
    if missing == 'PAIRWISE':
        use_pairwise = True

    arr = _as_fortran_2d(data)
    n_obs, n_vars = arr.shape
    if n_vars < 2:
        raise ValueError(f'{coeff_label} 相关至少需要 2 个变量')

    var_names = _resolve_columns(data, columns)
    if var_names is None:
        var_names = [f'V{i + 1}' for i in range(n_vars)]
    if len(var_names) != n_vars:
        raise ValueError(
            f'columns 长度 ({len(var_names)}) 与数据列数 ({n_vars}) 不一致'
        )

    corr = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    pval = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    counts = np.zeros(n_vars, dtype=np.int32)

    _algo.spearman_core.compute_spearman_kendall(
        data=arr,
        corr_type=corr_type,
        use_pairwise=1 if use_pairwise else 0,
        use_two_tails=1 if use_two_tails else 0,
        corr=corr, pval=pval, counts=counts,
    )

    corr_clean = np.where(
        (corr <= -1.0e35) | (~np.isfinite(corr)), np.nan, corr
    )
    pval_clean = np.where(
        (pval <= -1.0e35) | (~np.isfinite(pval)), np.nan, pval
    )

    idx = pd.Index(var_names, name='variable')
    correlations = pd.DataFrame(corr_clean, index=idx, columns=var_names)
    significance = pd.DataFrame(pval_clean, index=idx, columns=var_names)
    n_matrix = pd.DataFrame(
        np.tile(counts.reshape(-1, 1), (1, n_vars)),
        index=idx, columns=var_names,
    )

    return {
        'correlations': correlations,
        'significance_two_tailed': significance,
        'n_pairs': n_matrix,
        'coefficient_type': coeff_label,
        'meta': {
            'method': 'Spearman rho' if corr_type == _CORR_SPEARMAN else 'Kendall tau_b',
            'coefficient': coeff_label,
            'test_type': 'two-tailed' if use_two_tails else 'one-tailed',
            'missing': missing,
            'n_observations': int(n_obs),
            'n_variables': int(n_vars),
        },
    }


__all__ = ['run_spearman']
