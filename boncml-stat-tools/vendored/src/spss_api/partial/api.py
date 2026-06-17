#!/usr/bin/env python3
"""PARTIAL Python API (偏相关分析).

对应 SPSS 命令: PARTIAL CORR
路径: 分析 > 相关 > 偏相关

Fortran 入口:
    subroutine compute_partial(data, main_vars, control_vars, use_two_tails,
                               compute_stats, corr_partial, pval_partial,
                               counts, corr_zero, pval_zero, means_all, std_all)

变量索引: 1-based

输出表（参照 SPSS Partial Correlations 输出面板）:
    - partial_correlations      偏相关矩阵（n_main × n_main）
    - significance_two_tailed   偏相关显著性矩阵
    - n_pairs                   每主变量样本数
    - zero_order_correlations   零阶相关矩阵（包含 main + control 全部变量）
    - zero_order_significance   零阶显著性矩阵
    - descriptive_statistics    所有变量（main + control）的均值/标准差/n
    - meta                      控制变量列表 + 元信息
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

_algo = importlib.import_module('partial')


def _as_fortran_2d(data: Any) -> np.ndarray:
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


def _names_to_indices(names: List[str], full_list: List[str]) -> np.ndarray:
    """将变量名列表转为 1-based 索引数组（基于 full_list 的位置）."""
    idx_map = {n: i + 1 for i, n in enumerate(full_list)}
    missing = [n for n in names if n not in idx_map]
    if missing:
        raise ValueError(f'变量名不在数据列中: {missing}; 可用: {full_list}')
    return np.array([idx_map[n] for n in names], dtype=np.int32)


def run_partial(
    data: Any,
    main_variables: List[str],
    control_variables: List[str],
    columns: Optional[List[str]] = None,
    use_two_tails: bool = True,
) -> Dict[str, Any]:
    """计算偏相关系数矩阵（控制 control_variables 后 main_variables 间的相关）。

    参数:
        data              : (n_obs, n_vars) 二维数据
        main_variables    : 主变量名列表（计算偏相关的对象，至少 2 个）
        control_variables : 控制变量名列表（至少 1 个）
        columns           : 数据所有列名（可选，DataFrame 可省略）
        use_two_tails     : True=双尾（默认）

    返回:
        dict，含 partial_correlations / significance_two_tailed / n_pairs /
        zero_order_correlations / zero_order_significance /
        descriptive_statistics / meta 七个字段。
    """
    if not main_variables or len(main_variables) < 2:
        raise ValueError('main_variables 至少需要 2 个变量')
    if not control_variables:
        raise ValueError('control_variables 至少需要 1 个控制变量')

    overlap = set(main_variables) & set(control_variables)
    if overlap:
        raise ValueError(
            f'main_variables 与 control_variables 不能重叠: {sorted(overlap)}'
        )

    arr = _as_fortran_2d(data)
    n_obs, n_vars = arr.shape

    var_names = _resolve_columns(data, columns)
    if var_names is None:
        var_names = [f'V{i + 1}' for i in range(n_vars)]
    if len(var_names) != n_vars:
        raise ValueError(
            f'columns 长度 ({len(var_names)}) 与数据列数 ({n_vars}) 不一致'
        )

    # 校验所有传入变量都在 columns 中
    for v in list(main_variables) + list(control_variables):
        if v not in var_names:
            raise ValueError(f'变量 {v!r} 不在数据列中; 可用: {var_names}')

    # 转 1-based 索引
    main_idx = _names_to_indices(list(main_variables), var_names)
    ctrl_idx = _names_to_indices(list(control_variables), var_names)

    n_main = len(main_variables)
    n_ctrl = len(control_variables)
    p = n_main + n_ctrl  # 零阶矩阵的维度

    # 预分配输出
    corr_partial = np.zeros((n_main, n_main), dtype=np.float64, order='F')
    pval_partial = np.zeros((n_main, n_main), dtype=np.float64, order='F')
    counts = np.zeros(n_main, dtype=np.int32)
    corr_zero = np.zeros((p, p), dtype=np.float64, order='F')
    pval_zero = np.zeros((p, p), dtype=np.float64, order='F')
    means_all = np.zeros(p, dtype=np.float64)
    std_all = np.zeros(p, dtype=np.float64)

    _algo.partial_core.compute_partial(
        data=arr,
        main_vars=main_idx,
        control_vars=ctrl_idx,
        use_two_tails=1 if use_two_tails else 0,
        compute_stats=1,
        corr_partial=corr_partial,
        pval_partial=pval_partial,
        counts=counts,
        corr_zero=corr_zero,
        pval_zero=pval_zero,
        means_all=means_all,
        std_all=std_all,
    )

    # 清理 sentinel
    corr_p_clean = np.where(
        (corr_partial <= -1.0e35) | (~np.isfinite(corr_partial)),
        np.nan, corr_partial,
    )
    pval_p_clean = np.where(
        (pval_partial <= -1.0e35) | (~np.isfinite(pval_partial)),
        np.nan, pval_partial,
    )
    corr_z_clean = np.where(
        (corr_zero <= -1.0e35) | (~np.isfinite(corr_zero)),
        np.nan, corr_zero,
    )
    pval_z_clean = np.where(
        (pval_zero <= -1.0e35) | (~np.isfinite(pval_zero)),
        np.nan, pval_zero,
    )
    means_clean = np.array([_clean_scalar(m) for m in means_all], dtype=np.float64)
    stds_clean = np.array([_clean_scalar(s) for s in std_all], dtype=np.float64)

    # 装配 DataFrame
    main_idx_pd = pd.Index(main_variables, name='variable')
    all_vars_used = list(main_variables) + list(control_variables)
    all_idx_pd = pd.Index(all_vars_used, name='variable')

    partial_corr = pd.DataFrame(
        corr_p_clean, index=main_idx_pd, columns=main_variables
    )
    partial_sig = pd.DataFrame(
        pval_p_clean, index=main_idx_pd, columns=main_variables
    )
    partial_n = pd.DataFrame(
        np.tile(counts.reshape(-1, 1), (1, n_main)),
        index=main_idx_pd, columns=main_variables,
    )
    zero_corr = pd.DataFrame(
        corr_z_clean, index=all_idx_pd, columns=all_vars_used
    )
    zero_sig = pd.DataFrame(
        pval_z_clean, index=all_idx_pd, columns=all_vars_used
    )

    descriptive = pd.DataFrame({
        'variable': all_vars_used,
        'mean': means_clean,
        'std_deviation': stds_clean,
        'n': np.full(p, int(n_obs)),
    }).set_index('variable')

    return {
        'partial_correlations': partial_corr,
        'significance_two_tailed': partial_sig,
        'n_pairs': partial_n,
        'zero_order_correlations': zero_corr,
        'zero_order_significance': zero_sig,
        'descriptive_statistics': descriptive,
        'meta': {
            'method': 'Partial Correlation',
            'test_type': 'two-tailed' if use_two_tails else 'one-tailed',
            'main_variables': list(main_variables),
            'control_variables': list(control_variables),
            'n_observations': int(n_obs),
        },
    }


__all__ = ['run_partial']
