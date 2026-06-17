#!/usr/bin/env python3
"""DISTANCE Python API (距离/邻近度分析).

对应 SPSS 命令: PROXIMITIES
路径: 分析 > 相关 > 距离

支持 36 种度量：
  连续度量（9 种）：
    euclidean / squared_euclidean / city_block / chebyshev / minkowski /
    pearson / cosine / chi_square / phi_square
  二元度量（27 种）：
    russell_rao / simple_matching / jaccard / dice / ss1 / rogers_tanimoto /
    ss2 / kulczynski1 / ss3 / kulczynski2 / ss4 / hamann / ochiai / ss5 /
    phi / lambda / anderberg_d / yule_y / yule_q / binary_euclidean /
    size_diff / pattern_diff / binary_squared_euclidean / binary_shape_diff /
    dispersion / variance / lance_williams

7 种标准化方法：
  none / zscore / range_neg1_1 / range_0_1 / max_1 / mean_1 / sd_1

Fortran 入口:
    subroutine compute_distance(data, measure_type, between_cases, power, root,
                                distance, is_similarity,
                                standardize_method, standardize_by_case_flag,
                                use_absolute, use_reverse, use_rescale,
                                binary_present_value, binary_absent_value)

输出表（参照 SPSS Proximities 输出面板）:
    - proximity_matrix     N×N 距离/相似度矩阵
    - meta                 度量类型、方向、is_similarity 标志等
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

_algo = importlib.import_module('distance')


# 字符串 → Fortran measure_type 整数（与 distance_core.f90 中常量保持一致）
_MEASURE_MAP: Dict[str, int] = {
    # 连续度量
    'euclidean': 1,
    'cosine': 2,
    'minkowski': 3,
    'squared_euclidean': 4,
    'city_block': 5,
    'cityblock': 5,
    'manhattan': 5,
    'chebyshev': 6,
    'pearson': 7,
    'chi_square': 8,
    'chisq': 8,
    'phi_square': 9,
    # 二元度量
    'russell_rao': 10,
    'simple_matching': 11,
    'simplematching': 11,
    'jaccard': 12,
    'dice': 13,
    'ss1': 14,
    'sokal_sneath_1': 14,
    'rogers_tanimoto': 15,
    'ss2': 16,
    'sokal_sneath_2': 16,
    'kulczynski1': 17,
    'kulczynski_1': 17,
    'ss3': 18,
    'sokal_sneath_3': 18,
    'kulczynski2': 19,
    'kulczynski_2': 19,
    'ss4': 20,
    'sokal_sneath_4': 20,
    'hamann': 21,
    'ochiai': 22,
    'ss5': 23,
    'sokal_sneath_5': 23,
    'phi': 24,
    'phi_coefficient': 24,
    'lambda': 25,
    'goodman_kruskal_lambda': 25,
    'anderberg_d': 26,
    'yule_y': 27,
    'yule_q': 28,
    'binary_euclidean': 29,
    'size_diff': 30,
    'size_difference': 30,
    'pattern_diff': 31,
    'pattern_difference': 31,
    'binary_squared_euclidean': 32,
    'binary_shape_diff': 33,
    'binary_shape_difference': 33,
    'dispersion': 34,
    'variance': 35,
    'lance_williams': 36,
    'bray_curtis': 36,
}

# SPSS 官方度量名称（用于元信息显示）
_MEASURE_DISPLAY: Dict[int, str] = {
    1: 'Euclidean Distance',
    2: 'Cosine Similarity',
    3: 'Minkowski Distance',
    4: 'Squared Euclidean Distance',
    5: 'City Block (Manhattan) Distance',
    6: 'Chebyshev Distance',
    7: 'Pearson Correlation',
    8: 'Chi-square Measure',
    9: 'Phi-square Measure',
    10: 'Russell and Rao',
    11: 'Simple Matching',
    12: 'Jaccard',
    13: 'Dice',
    14: 'Sokal and Sneath 1',
    15: 'Rogers and Tanimoto',
    16: 'Sokal and Sneath 2',
    17: 'Kulczynski 1',
    18: 'Sokal and Sneath 3',
    19: 'Kulczynski 2',
    20: 'Sokal and Sneath 4',
    21: 'Hamann',
    22: 'Ochiai',
    23: 'Sokal and Sneath 5',
    24: 'Phi (4-fold point correlation)',
    25: 'Lambda (Goodman and Kruskal)',
    26: 'Anderberg D',
    27: 'Yule Y',
    28: 'Yule Q',
    29: 'Binary Euclidean Distance',
    30: 'Size Difference',
    31: 'Pattern Difference',
    32: 'Binary Squared Euclidean Distance',
    33: 'Binary Shape Difference',
    34: 'Dispersion',
    35: 'Variance',
    36: 'Lance and Williams',
}

_STANDARDIZE_MAP: Dict[str, int] = {
    'none': 0,
    'zscore': 1,
    'range_neg1_1': 2,
    'range_0_1': 3,
    'max_1': 4,
    'mean_1': 5,
    'sd_1': 6,
}

# 标识哪些 measure 是二元度量（值 ∈ {0,1}）
_BINARY_MEASURES = set(range(10, 37))


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


def _resolve_columns(data: Any, columns: Optional[List[str]]) -> Optional[List[str]]:
    if columns is not None:
        if not columns:
            raise ValueError('columns 不能为空')
        return list(columns)
    if isinstance(data, pd.DataFrame):
        return [str(c) for c in data.columns]
    return None


def run_distance(
    data: Any,
    columns: Optional[List[str]] = None,
    measure: str = 'euclidean',
    between: str = 'cases',
    power: int = 2,
    root: int = 2,
    standardize: str = 'none',
    standardize_by_case: bool = False,
    use_absolute: bool = False,
    use_reverse: bool = False,
    use_rescale: bool = False,
    binary_present_value: int = 1,
    binary_absent_value: int = 0,
) -> Dict[str, Any]:
    """计算距离矩阵或相似度矩阵（PROXIMITIES）。

    参数:
        data                 : (n_obs, n_vars) 二维数据
        columns              : 变量名列表（可选）
        measure              : 度量名（如 'euclidean'、'cosine'、'minkowski'、'pearson' 等）
        between              : 'cases'（个案间，默认）或 'variables'（变量间）
        power                : Minkowski 幂参数（仅 measure='minkowski' 时使用，默认 2）
        root                 : Minkowski 根参数（默认 2）
        standardize          : 标准化方法（默认 'none'）
        standardize_by_case  : True=按个案标准化（默认按变量）
        use_absolute         : True=应用绝对值转换
        use_reverse          : True=应用符号反转
        use_rescale          : True=重标度到 [0,1]
        binary_present_value : 二元度量的"存在"值（默认 1）
        binary_absent_value  : 二元度量的"不存在"值（默认 0）

    返回:
        dict，含 proximity_matrix / meta 两个字段。
    """
    measure_key = (measure or 'euclidean').lower()
    if measure_key not in _MEASURE_MAP:
        raise ValueError(
            f"未知 measure {measure!r}; 可用: {sorted(set(_MEASURE_MAP.keys()))}"
        )
    measure_type = _MEASURE_MAP[measure_key]
    is_binary = measure_type in _BINARY_MEASURES

    between_key = (between or 'cases').lower()
    if between_key not in ('cases', 'variables'):
        raise ValueError(f"between 仅支持 'cases' / 'variables'，当前: {between}")
    between_cases = (between_key == 'cases')

    std_key = (standardize or 'none').lower()
    if std_key not in _STANDARDIZE_MAP:
        raise ValueError(
            f"未知 standardize {standardize!r}; 可用: {sorted(_STANDARDIZE_MAP.keys())}"
        )
    standardize_method = _STANDARDIZE_MAP[std_key]

    arr = _as_fortran_2d(data)
    n_obs, n_vars = arr.shape

    var_names = _resolve_columns(data, columns)
    if var_names is None:
        var_names = [f'V{i + 1}' for i in range(n_vars)]
    if len(var_names) != n_vars:
        raise ValueError(
            f'columns 长度 ({len(var_names)}) 与数据列数 ({n_vars}) 不一致'
        )

    # 输出矩阵维度：between_cases → n_obs×n_obs，否则 n_vars×n_vars
    n_out = n_obs if between_cases else n_vars
    distance = np.zeros((n_out, n_out), dtype=np.float64, order='F')

    is_sim_int = _algo.distance_core.compute_distance(
        data=arr,
        measure_type=measure_type,
        between_cases=1 if between_cases else 0,
        power=int(power),
        root=int(root),
        distance=distance,
        standardize_method=standardize_method,
        standardize_by_case_flag=1 if standardize_by_case else 0,
        use_absolute=1 if use_absolute else 0,
        use_reverse=1 if use_reverse else 0,
        use_rescale=1 if use_rescale else 0,
        binary_present_value=int(binary_present_value),
        binary_absent_value=int(binary_absent_value),
    )

    # 清理 sentinel
    prox_clean = np.where(
        (distance <= -1.0e35) | (~np.isfinite(distance)), np.nan, distance
    )

    labels = [f'Case {i + 1}' for i in range(n_obs)] if between_cases else var_names
    label_name = 'case' if between_cases else 'variable'
    idx = pd.Index(labels, name=label_name)
    prox_df = pd.DataFrame(prox_clean, index=idx, columns=labels)

    is_similarity_bool = bool(is_sim_int)
    matrix_type = 'Similarity' if is_similarity_bool else 'Dissimilarity'

    return {
        'proximity_matrix': prox_df,
        'meta': {
            'method': 'Proximities',
            'measure': measure_key,
            'measure_display': _MEASURE_DISPLAY.get(measure_type, measure_key),
            'measure_type': measure_type,
            'is_binary_measure': is_binary,
            'proximity_between': between_key,
            'matrix_type': matrix_type,
            'is_similarity': is_similarity_bool,
            'standardize': std_key,
            'power': int(power) if measure_key == 'minkowski' else None,
            'root': int(root) if measure_key == 'minkowski' else None,
            'n_observations': int(n_obs),
            'n_variables': int(n_vars),
        },
    }


__all__ = ['run_distance']
