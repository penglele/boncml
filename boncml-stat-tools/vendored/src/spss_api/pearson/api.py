#!/usr/bin/env python3
"""PEARSON Python API (皮尔逊相关系数分析).

对应 SPSS 命令: CORRELATIONS
路径: 分析 > 相关 > 双变量 > 皮尔逊

Fortran 入口:
    subroutine compute_pearson(data, use_two_tails, use_pairwise,
                               corr, pval, counts, means, sscp, cov)

输出表（参照 SPSS Correlations 输出面板）:
    - correlations              Pearson 相关系数矩阵（含对角线 1.000）
    - significance_two_tailed   显著性（双尾 p 值）矩阵
    - n_pairs                   每变量的样本数
    - descriptive_statistics    描述性统计（n、均值、标准差）
    - covariances               协方差矩阵
    - sums_of_squares_and_cross_products  SSCP 矩阵

注意:
    - 当前 Fortran 实现是简化版（listwise 处理，不实现 pairwise 缺失值）
    - counts 是 1D（每变量样本数），非 SPSS 标准的 N×N 矩阵
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

_algo = importlib.import_module('pearson')


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


def _resolve_columns(data: Any, columns: Optional[List[str]]) -> List[str]:
    """优先用显式传入的 columns；其次用 DataFrame 列名；最后回退 V1/V2/..."""
    if columns is not None:
        if not columns:
            raise ValueError('columns 不能为空')
        return list(columns)
    if isinstance(data, pd.DataFrame):
        return [str(c) for c in data.columns]
    return None  # 调用方在知道 n_vars 后再回退


def _clean_scalar(value: Any) -> Optional[float]:
    """清理 Fortran 返回的 sentinel（-1e308 等）→ None."""
    val = float(value)
    if not np.isfinite(val) or val <= -1.0e35:
        return None
    return val


def run_pearson(
    data: Any,
    columns: Optional[List[str]] = None,
    use_two_tails: bool = True,
    use_pairwise: bool = False,
    missing: str = 'LISTWISE',
) -> Dict[str, Any]:
    """计算 Pearson 相关系数矩阵及显著性。

    参数:
        data           : (n_obs, n_vars) 二维数据，支持 numpy / list / pandas DataFrame
        columns        : 变量名列表（可选）。若 data 是 DataFrame 可省略
        use_two_tails  : True=双尾检验（默认），False=单尾
        use_pairwise   : True=逐对（当前实现未实际生效，listwise 模式）
        missing        : 'LISTWISE' 或 'PAIRWISE'（当前仅 LISTWISE 生效）

    返回:
        dict，含 correlations / significance_two_tailed / n_pairs /
        descriptive_statistics / covariances /
        sums_of_squares_and_cross_products 六张表。
    """
    missing = (missing or 'LISTWISE').upper()
    if missing not in ('LISTWISE', 'PAIRWISE'):
        raise ValueError(f"missing 仅支持 'LISTWISE' / 'PAIRWISE'，当前: {missing}")
    if missing == 'PAIRWISE':
        use_pairwise = True

    arr = _as_fortran_2d(data)
    n_obs, n_vars = arr.shape
    if n_vars < 2:
        raise ValueError('Pearson 相关至少需要 2 个变量')

    var_names = _resolve_columns(data, columns)
    if var_names is None:
        var_names = [f'V{i + 1}' for i in range(n_vars)]
    if len(var_names) != n_vars:
        raise ValueError(
            f'columns 长度 ({len(var_names)}) 与数据列数 ({n_vars}) 不一致'
        )

    # 预分配输出数组（Fortran intent(inout)）
    corr = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    pval = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    counts = np.zeros(n_vars, dtype=np.int32)
    means = np.zeros(n_vars, dtype=np.float64)
    sscp = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    cov = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')

    _algo.pearson_core.compute_pearson(
        data=arr,
        use_two_tails=1 if use_two_tails else 0,
        use_pairwise=1 if use_pairwise else 0,
        corr=corr, pval=pval, counts=counts,
        means=means, sscp=sscp, cov=cov,
    )

    # 清理 Fortran sentinel → None / NaN
    corr_clean = np.where(
        (corr <= -1.0e35) | (~np.isfinite(corr)), np.nan, corr
    )
    pval_clean = np.where(
        (pval <= -1.0e35) | (~np.isfinite(pval)), np.nan, pval
    )
    means_clean = np.array([_clean_scalar(m) for m in means], dtype=np.float64)

    # 标准差：从 SSCP 对角线 = sum((x-mean)^2)；std = sqrt(sscp_i / (n-1))
    n_for_std = np.maximum(counts - 1, 1).astype(np.float64)
    var_diag = np.diag(sscp).astype(np.float64)
    var_diag = np.where(var_diag <= -1.0e35, np.nan, var_diag)
    stds = np.sqrt(var_diag / n_for_std)
    stds = np.where(stds < 0, np.nan, stds)

    # 装配 DataFrame（行列索引均为变量名）
    idx = pd.Index(var_names, name='variable')
    correlations = pd.DataFrame(corr_clean, index=idx, columns=var_names)
    significance = pd.DataFrame(pval_clean, index=idx, columns=var_names)

    # SPSS 风格的 N 矩阵：listwise 下全部相同（每变量 counts[i]）
    # 当前 Fortran 简化实现下，counts[i] 即 n_obs（缺失值未剔除）
    n_matrix = pd.DataFrame(
        np.tile(counts.reshape(-1, 1), (1, n_vars)),
        index=idx, columns=var_names,
    )

    descriptive = pd.DataFrame({
        'variable': var_names,
        'mean': means_clean,
        'std_deviation': stds,
        'n': counts.astype(int),
    }).set_index('variable')

    covariances = pd.DataFrame(cov, index=idx, columns=var_names)
    sscp_df = pd.DataFrame(sscp, index=idx, columns=var_names)

    return {
        'correlations': correlations,
        'significance_two_tailed': significance,
        'n_pairs': n_matrix,
        'descriptive_statistics': descriptive,
        'covariances': covariances,
        'sums_of_squares_and_cross_products': sscp_df,
        'meta': {
            'method': 'Pearson',
            'test_type': 'two-tailed' if use_two_tails else 'one-tailed',
            'missing': missing,
            'n_observations': int(n_obs),
            'n_variables': int(n_vars),
        },
    }


__all__ = ['run_pearson']
