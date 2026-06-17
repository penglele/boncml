#!/usr/bin/env python3
"""ROC Python API (受试者工作特征曲线分析).

对应 SPSS 命令: ROC
路径: 分析 > ROC 曲线

Fortran 入口:
    subroutine compute_roc_curve(test_vars, state_var,
                                 larger_is_positive, include_boundary,
                                 compute_se, dist_type, ci_level,
                                 auc, auc_se, auc_sig, ci_lower, ci_upper,
                                 n_cutoffs, cutoffs, sensitivity, one_minus_spec)

输出表（参照 SPSS ROC Curve 输出面板）:
    - area_under_curve          每个 test_var 的 AUC + SE + Sig + CI
    - case_processing_summary   总数/有效/缺失/阳性/阴性
    - coordinates_of_curve      每个 test_var 的 cutoff/sensitivity/specificity
    - meta                      分布类型、CI 级别、阳性值等

注意:
    - Fortran 简化实现，不处理缺失值
    - cutoffs/sensitivity/one_minus_spec 是变长（按 n_cutoffs 切片）
    - Case processing summary 由 Python 层从 state_var 计算
"""
import importlib
import os
import sys
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

here = os.path.abspath(os.path.dirname(__file__))
lib_dir = os.path.normpath(os.path.join(here, '..', '..', '..', 'lib'))
src_dir = os.path.normpath(os.path.join(here, '..', '..'))
for path in (lib_dir, src_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

_algo = importlib.import_module('roc')

DIST_TYPE_NONPARAMETRIC = 0
DIST_TYPE_BINEXP = 1


def _as_fortran_2d(data: Any) -> np.ndarray:
    if isinstance(data, pd.DataFrame):
        arr = data.to_numpy(dtype=np.float64)
    elif isinstance(data, pd.Series):
        arr = data.to_numpy(dtype=np.float64).reshape(-1, 1)
    else:
        arr = np.asarray(data, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError('test_vars 必须是二维数组 (n_obs, n_vars) 或 DataFrame')
    return np.asfortranarray(arr)


def _clean_scalar(value: Any) -> Optional[float]:
    val = float(value)
    if not np.isfinite(val) or val <= -1.0e35:
        return None
    return val


def _resolve_columns(data: Any, columns: Optional[List[str]]) -> Optional[List[str]]:
    if columns is not None:
        if not columns:
            raise ValueError('columns 不能为空')
        return list(columns)
    if isinstance(data, pd.DataFrame):
        return [str(c) for c in data.columns]
    return None


def run_roc(
    data: Any,
    state_variable: str,
    positive_value: Union[int, float, str] = 1,
    test_variables: Optional[List[str]] = None,
    columns: Optional[List[str]] = None,
    larger_is_positive: bool = True,
    include_boundary: bool = True,
    distribution: str = 'nonparametric',
    ci_level: float = 95.0,
) -> Dict[str, Any]:
    """计算 ROC 曲线（受试者工作特征）。

    参数:
        data               : (n_obs, n_vars) 二维数据（含 test 变量与 state 变量）
                             支持 numpy / list / DataFrame
        state_variable     : 二分类金标准变量名（或在 columns 中的列名）
        positive_value     : 阳性状态值（默认 1）。整数/浮点/字符串皆可
        test_variables     : 评估的诊断变量名列表（默认 = 除 state 外所有数值列）
        columns            : 数据所有列名（可选，DataFrame 可省略）
        larger_is_positive : True=值越大越像阳性（默认）
        include_boundary   : True=cutoff 用 >= 比较（默认），False=>
        distribution       : 'nonparametric'（默认）或 'binexp'
        ci_level           : 置信度（默认 95.0）

    返回:
        dict，含 area_under_curve / case_processing_summary /
        coordinates_of_curve / meta 四个字段。
    """
    if not isinstance(data, pd.DataFrame):
        raise ValueError(
            'ROC 分析需要传入 pandas DataFrame（含 state_variable 列）'
        )

    dist_key = (distribution or 'nonparametric').lower()
    if dist_key not in ('nonparametric', 'binexp'):
        raise ValueError(f"distribution 仅支持 'nonparametric' / 'binexp'，当前: {distribution}")
    dist_type = DIST_TYPE_NONPARAMETRIC if dist_key == 'nonparametric' else DIST_TYPE_BINEXP

    # 解析 test_variables
    all_cols = list(data.columns)
    if state_variable not in all_cols:
        raise ValueError(f"state_variable {state_variable!r} 不在数据列中; 可用: {all_cols}")

    if test_variables is None:
        test_variables = [
            c for c in all_cols
            if c != state_variable and pd.api.types.is_numeric_dtype(data[c])
        ]
    if not test_variables:
        raise ValueError('test_variables 不能为空（也未自动找到数值列）')

    # state_var 提取 + 阳性值编码
    state_col = data[state_variable]
    if pd.api.types.is_numeric_dtype(state_col):
        state_arr = state_col.to_numpy(dtype=np.float64)
        pos_val_num = float(positive_value)
    else:
        # 字符串/分类型：编码为 1.0=positive, 0.0=negative
        codes = (state_col.astype(str) == str(positive_value)).astype(np.float64).to_numpy()
        state_arr = codes
        pos_val_num = 1.0

    # 阳性/阴性计数
    is_pos = state_arr == pos_val_num
    n_positive = int(np.sum(is_pos))
    n_negative = int(np.sum(~is_pos))
    n_total = int(len(state_arr))
    n_valid = n_positive + n_negative
    n_missing = n_total - n_valid

    # test_vars 矩阵
    test_df = data[test_variables].apply(pd.to_numeric, errors='coerce')
    test_arr = _as_fortran_2d(test_df)
    n_obs, n_test = test_arr.shape

    # 预分配
    auc = np.zeros(n_test, dtype=np.float64)
    auc_se = np.zeros(n_test, dtype=np.float64)
    auc_sig = np.zeros(n_test, dtype=np.float64)
    ci_lower = np.zeros(n_test, dtype=np.float64)
    ci_upper = np.zeros(n_test, dtype=np.float64)
    n_cutoffs = np.zeros(n_test, dtype=np.int32)
    max_cutoffs = n_obs + 2  # 最大可能的 cutoff 数
    cutoffs = np.zeros((max_cutoffs, n_test), dtype=np.float64, order='F')
    sensitivity = np.zeros((max_cutoffs, n_test), dtype=np.float64, order='F')
    one_minus_spec = np.zeros((max_cutoffs, n_test), dtype=np.float64, order='F')

    _algo.roc_core.compute_roc_curve(
        test_vars=test_arr,
        state_var=state_arr,
        auc=auc, auc_se=auc_se, auc_sig=auc_sig,
        ci_lower=ci_lower, ci_upper=ci_upper,
        n_cutoffs=n_cutoffs,
        cutoffs=cutoffs, sensitivity=sensitivity, one_minus_spec=one_minus_spec,
        larger_is_positive=1 if larger_is_positive else 0,
        include_boundary=1 if include_boundary else 0,
        compute_se=1,
        dist_type=dist_type,
        ci_level=float(ci_level),
    )

    # AUC 表
    auc_table = pd.DataFrame({
        'test_variable': test_variables,
        'area': auc,
        'std_error': auc_se,
        'significance': auc_sig,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
    })

    # Coordinates 切片（变长）
    coords = []
    for i, tvar in enumerate(test_variables):
        n_cut = int(n_cutoffs[i])
        coords.append({
            'test_variable': tvar,
            'cutoffs': cutoffs[:n_cut, i].tolist(),
            'sensitivity': sensitivity[:n_cut, i].tolist(),
            'specificity': (1.0 - one_minus_spec[:n_cut, i]).tolist(),
        })

    case_summary = {
        'total_cases': n_total,
        'valid_cases': n_valid,
        'missing_cases': n_missing,
        'positive_cases': n_positive,
        'negative_cases': n_negative,
        'positive_value': positive_value,
    }

    return {
        'area_under_curve': auc_table,
        'case_processing_summary': case_summary,
        'coordinates_of_curve': coords,
        'meta': {
            'method': 'ROC Curve',
            'distribution': 'nonparametric' if dist_type == DIST_TYPE_NONPARAMETRIC else 'bi-negative exponential',
            'ci_level': float(ci_level),
            'larger_is_positive': bool(larger_is_positive),
            'include_boundary': bool(include_boundary),
            'state_variable': state_variable,
            'positive_value': positive_value,
            'test_variables': list(test_variables),
            'n_observations': n_obs,
        },
    }


__all__ = ['run_roc']
