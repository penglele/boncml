#!/usr/bin/env python3
"""FACTOR Python API (因子分析 / 主成分分析).

对应 SPSS 命令: FACTOR
路径: 分析 > 降维 > 因子

包含 7 种提取方法、6 种旋转、3 种得分法。**主成分分析（PCA）通过
extraction_method='pca' 走同一接口**，无需单独的 princa 算法。

提取方法（extraction_method）:
    pca / paf / alpha / image / uls / gls / ml

旋转方法（rotation_method）:
    none / varimax / equamax / quartimax / oblimin / promax

得分方法（score_method）:
    regression / bartlett / anderson_rubin

Fortran 入口:
    compute_factor(data, extr_method, rot_method,
                   eigenvalues, eigenvectors, loadings, rotated_loadings,
                   scores, variance_explained, cumulative_variance,
                   n_factors_extracted, score_coefficient_matrix,
                   initial_eigenvalues, initial_variance_explained,
                   initial_cumulative_variance, ...50+ 输出)

输出表（参照 SPSS Factor Analysis 输出面板）:
    - kmo_and_bartlett_test       KMO + Bartlett 球形检验
    - communalities               公因子方差（initial/extraction × raw/rescaled）
    - total_variance_explained    总方差解释（initial/extraction/rotation 三段）
    - factor_matrix               未旋转载荷
    - rotated_factor_matrix       旋转后载荷（无旋转时为 None）
    - structure_matrix            结构矩阵（oblique 旋转才有意义）
    - factor_score_coefficients   因子得分系数矩阵
    - factor_scores               因子得分（n_obs × n_factors）
    - factor_correlation_matrix   因子间相关（oblique 旋转才有意义）
    - descriptive_statistics      描述性统计
    - meta                        方法选择等元信息
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

_algo = importlib.import_module('factor')

# 提取方法
_EXTR_MAP: Dict[str, int] = {
    'pca': 1,
    'principal_components': 1,
    'paf': 2,
    'principal_axis': 2,
    'principal_axis_factoring': 2,
    'alpha': 3,
    'alpha_factoring': 3,
    'image': 4,
    'image_factoring': 4,
    'uls': 5,
    'unweighted_least_squares': 5,
    'gls': 6,
    'generalized_least_squares': 6,
    'ml': 7,
    'maximum_likelihood': 7,
}

# 旋转方法
_ROT_MAP: Dict[str, int] = {
    'none': 1,
    'varimax': 2,
    'equamax': 3,
    'quartimax': 4,
    'oblimin': 5,
    'promax': 7,
}

# 得分方法
_SCORE_MAP: Dict[str, int] = {
    'regression': 1,
    'bartlett': 2,
    'anderson_rubin': 3,
    'andersonrubin': 3,
}

# 矩阵类型
_MATRIX_MAP: Dict[str, int] = {
    'correlation': 0,
    'covariance': 1,
}

# oblique 旋转集合
_OBLIQUE_ROT = {'oblimin', 'promax'}

# 显示名
_EXTR_DISPLAY: Dict[int, str] = {
    1: 'Principal Components',
    2: 'Principal Axis Factoring',
    3: 'Alpha Factoring',
    4: 'Image Factoring',
    5: 'Unweighted Least Squares',
    6: 'Generalized Least Squares',
    7: 'Maximum Likelihood',
}
_ROT_DISPLAY: Dict[int, str] = {
    1: 'None',
    2: 'Varimax',
    3: 'Equamax',
    4: 'Quartimax',
    5: 'Oblimin',
    7: 'Promax',
}
_SCORE_DISPLAY: Dict[int, str] = {
    1: 'Regression',
    2: 'Bartlett',
    3: 'Anderson-Rubin',
}


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


def _clean_scalar(v: Any) -> Optional[float]:
    val = float(v)
    if not np.isfinite(val) or val <= -1.0e35:
        return None
    return val


def _factor_names(n_factors: int, prefix: str = 'Component') -> List[str]:
    return [f'{prefix} {i + 1}' for i in range(n_factors)]


def run_factor(
    data: Any,
    columns: Optional[List[str]] = None,
    extraction_method: str = 'pca',
    rotation_method: str = 'none',
    score_method: str = 'regression',
    n_factors: Optional[int] = None,
    max_iter: int = 25,
    matrix_type: str = 'correlation',
) -> Dict[str, Any]:
    """计算因子分析或主成分分析。

    参数:
        data             : (n_obs, n_vars) 二维数据
        columns          : 变量名列表（可选）
        extraction_method: 'pca'(默认)/'paf'/'alpha'/'image'/'uls'/'gls'/'ml'
        rotation_method  : 'none'(默认)/'varimax'/'equamax'/'quartimax'/'oblimin'/'promax'
        score_method     : 'regression'(默认)/'bartlett'/'anderson_rubin'
        n_factors        : 提取的因子数（默认 None = 自动，由 Fortran 决定）
        max_iter         : 最大迭代次数（默认 25）
        matrix_type      : 'correlation'(默认) 或 'covariance'

    返回:
        dict，含 kmo_and_bartlett_test / communalities / total_variance_explained /
        factor_matrix / rotated_factor_matrix / structure_matrix /
        factor_score_coefficients / factor_scores / factor_correlation_matrix /
        descriptive_statistics / meta 字段。
    """
    extr_key = (extraction_method or 'pca').lower()
    if extr_key not in _EXTR_MAP:
        raise ValueError(
            f"未知 extraction_method {extraction_method!r}; 可用: {sorted(set(_EXTR_MAP.keys()))}"
        )
    extr_int = _EXTR_MAP[extr_key]

    rot_key = (rotation_method or 'none').lower()
    if rot_key not in _ROT_MAP:
        raise ValueError(
            f"未知 rotation_method {rotation_method!r}; 可用: {sorted(_ROT_MAP.keys())}"
        )
    rot_int = _ROT_MAP[rot_key]
    is_oblique = rot_key in _OBLIQUE_ROT

    score_key = (score_method or 'regression').lower()
    if score_key not in _SCORE_MAP:
        raise ValueError(
            f"未知 score_method {score_method!r}; 可用: {sorted(_SCORE_MAP.keys())}"
        )
    score_int = _SCORE_MAP[score_key]

    mat_key = (matrix_type or 'correlation').lower()
    if mat_key not in _MATRIX_MAP:
        raise ValueError(f"matrix_type 仅支持 'correlation'/'covariance'，当前: {matrix_type}")
    mat_int = _MATRIX_MAP[mat_key]

    arr = _as_fortran_2d(data)
    n_obs, n_vars = arr.shape
    if n_vars < 2:
        raise ValueError('因子分析至少需要 2 个变量')

    var_names = _resolve_columns(data, columns)
    if var_names is None:
        var_names = [f'V{i + 1}' for i in range(n_vars)]
    if len(var_names) != n_vars:
        raise ValueError(
            f'columns 长度 ({len(var_names)}) 与数据列数 ({n_vars}) 不一致'
        )

    # 提取因子数：未指定时用 n_vars（让 Fortran 自己决定）
    n_factors_in = int(n_factors) if n_factors else n_vars

    # 预分配所有输出数组
    eigenvalues = np.zeros(n_vars, dtype=np.float64)
    eigenvectors = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    loadings = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    rotated_loadings = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    scores = np.zeros((n_obs, n_vars), dtype=np.float64, order='F')
    variance_explained = np.zeros(n_vars, dtype=np.float64)
    cumulative_variance = np.zeros(n_vars, dtype=np.float64)
    n_factors_extracted = np.zeros(1, dtype=np.int32)
    score_coefficient_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    initial_eigenvalues = np.zeros(n_vars, dtype=np.float64)
    initial_variance_explained = np.zeros(n_vars, dtype=np.float64)
    initial_cumulative_variance = np.zeros(n_vars, dtype=np.float64)

    # 标量输出（rank-0）
    univariate_mean = np.zeros(1, dtype=np.float64)
    univariate_std = np.zeros(1, dtype=np.float64)
    n_valid = np.zeros(1, dtype=np.int32)
    correlation_determinant = np.zeros(1, dtype=np.float64)
    kmo = np.zeros(1, dtype=np.float64)
    bartlett_chi2 = np.zeros(1, dtype=np.float64)
    bartlett_df = np.zeros(1, dtype=np.float64)
    bartlett_sig = np.zeros(1, dtype=np.float64)

    # 实际 univariate_mean/std 是 1D（每变量一个值）
    # f2py 标记为 rank-0 但实际接收数组，先按 1D 准备，编译期会调整
    # 修正：根据 .pyf intent(inout) rank-1 才合理。看 .so doc:
    #   univariate_mean : in/output rank-1 array('d')
    # 所以这些应该是 1D
    univariate_mean = np.zeros(n_vars, dtype=np.float64)
    univariate_std = np.zeros(n_vars, dtype=np.float64)

    # 矩阵输出
    factor_correlation_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    reproduced_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    anti_image_correlation = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    anti_image_covariance_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    correlation_significance = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    correlation_inverse = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')

    # 公因子方差（每变量）
    communalities = np.zeros(n_vars, dtype=np.float64)
    communalities_initial_raw = np.zeros(n_vars, dtype=np.float64)
    communalities_extraction_raw = np.zeros(n_vars, dtype=np.float64)
    communalities_initial_rescaled = np.zeros(n_vars, dtype=np.float64)
    communalities_extraction_rescaled = np.zeros(n_vars, dtype=np.float64)
    # SPSS 个案选择变量(本接口不暴露,默认禁用:全部参与分析)
    selection_var = np.ones(n_obs, dtype=np.float64)
    # f2py 错误信息缓冲区(Fortran 写入错误描述, ierr!=0 时有意义)
    err_msg = np.array(" " * 256, dtype="c")

    # 旋转相关
    factor_transformation_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    structure_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    image_covariance_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    component_score_covariance_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    analysis_dispersion_matrix = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')

    goodness_of_fit_chi_square = np.zeros(1, dtype=np.float64)
    goodness_of_fit_df = np.zeros(1, dtype=np.float64)
    goodness_of_fit_sig = np.zeros(1, dtype=np.float64)

    rotation_sum_squared_loadings = np.zeros(n_vars, dtype=np.float64)
    rotation_variance_explained = np.zeros(n_vars, dtype=np.float64)
    rotation_cumulative_variance = np.zeros(n_vars, dtype=np.float64)
    rotated_loadings_rescaled = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    extraction_sum_squared_loadings_rescaled = np.zeros(n_vars, dtype=np.float64)
    extraction_variance_explained_rescaled = np.zeros(n_vars, dtype=np.float64)
    extraction_cumulative_variance_rescaled = np.zeros(n_vars, dtype=np.float64)
    rotation_sum_squared_loadings_rescaled = np.zeros(n_vars, dtype=np.float64)
    rotation_variance_explained_rescaled = np.zeros(n_vars, dtype=np.float64)
    rotation_cumulative_variance_rescaled = np.zeros(n_vars, dtype=np.float64)
    loadings_rescaled = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')
    structure_matrix_rescaled = np.zeros((n_vars, n_vars), dtype=np.float64, order='F')

    ierr = _algo.factor_core.compute_factor(
        data=arr,
        extr_method=extr_int,
        rot_method=rot_int,
        eigenvalues=eigenvalues,
        eigenvectors=eigenvectors,
        loadings=loadings,
        rotated_loadings=rotated_loadings,
        scores=scores,
        variance_explained=variance_explained,
        cumulative_variance=cumulative_variance,
        n_factors_extracted=n_factors_extracted,
        score_coefficient_matrix=score_coefficient_matrix,
        initial_eigenvalues=initial_eigenvalues,
        initial_variance_explained=initial_variance_explained,
        initial_cumulative_variance=initial_cumulative_variance,
        matrix_type=mat_int,
        n_factors=n_factors_in,
        max_iter=int(max_iter),
        score_method=score_int,
        selection_enabled=0,
        selection_var=selection_var,
        factor_correlation_matrix=factor_correlation_matrix,
        univariate_mean=univariate_mean,
        univariate_std=univariate_std,
        n_valid=n_valid,
        correlation_determinant=correlation_determinant,
        kmo=kmo,
        bartlett_chi2=bartlett_chi2,
        bartlett_df=bartlett_df,
        bartlett_sig=bartlett_sig,
        reproduced_matrix=reproduced_matrix,
        anti_image_correlation=anti_image_correlation,
        anti_image_covariance_matrix=anti_image_covariance_matrix,
        correlation_significance=correlation_significance,
        correlation_inverse=correlation_inverse,
        communalities_extraction_rescaled=communalities_extraction_rescaled,
        communalities_initial_rescaled=communalities_initial_rescaled,
        communalities_initial_raw=communalities_initial_raw,
        communalities_extraction_raw=communalities_extraction_raw,
        factor_transformation_matrix=factor_transformation_matrix,
        structure_matrix=structure_matrix,
        image_covariance_matrix=image_covariance_matrix,
        component_score_covariance_matrix=component_score_covariance_matrix,
        analysis_dispersion_matrix=analysis_dispersion_matrix,
        goodness_of_fit_chi_square=goodness_of_fit_chi_square,
        goodness_of_fit_df=goodness_of_fit_df,
        goodness_of_fit_sig=goodness_of_fit_sig,
        rotation_sum_squared_loadings=rotation_sum_squared_loadings,
        rotation_variance_explained=rotation_variance_explained,
        rotation_cumulative_variance=rotation_cumulative_variance,
        rotated_loadings_rescaled=rotated_loadings_rescaled,
        extraction_sum_squared_loadings_rescaled=extraction_sum_squared_loadings_rescaled,
        extraction_variance_explained_rescaled=extraction_variance_explained_rescaled,
        extraction_cumulative_variance_rescaled=extraction_cumulative_variance_rescaled,
        rotation_sum_squared_loadings_rescaled=rotation_sum_squared_loadings_rescaled,
        rotation_variance_explained_rescaled=rotation_variance_explained_rescaled,
        rotation_cumulative_variance_rescaled=rotation_cumulative_variance_rescaled,
        loadings_rescaled=loadings_rescaled,
        structure_matrix_rescaled=structure_matrix_rescaled,
        err_msg=err_msg,
    )

    n_extracted = int(n_factors_extracted[0])
    if ierr != 0:
        raise RuntimeError(
            f'compute_factor 返回 ierr={ierr}（Fortran 内部错误，可能奇异矩阵或 max_iter 不足）'
        )

    # 切片到实际提取的因子数
    comp_names = _factor_names(n_extracted, prefix='Component')
    var_idx = pd.Index(var_names, name='variable')

    # KMO + Bartlett
    kmo_bartlett = {
        'kmo': _clean_scalar(kmo[0]),
        'bartlett_test_of_sphericity': {
            'chi_square': _clean_scalar(bartlett_chi2[0]),
            'df': _clean_scalar(bartlett_df[0]),
            'significance': _clean_scalar(bartlett_sig[0]),
        },
    }

    # 公因子方差
    communalities_df = pd.DataFrame({
        'variable': var_names,
        'initial': communalities_initial_raw[:n_vars],
        'extraction': communalities_extraction_raw[:n_vars],
    }).set_index('variable')

    # 总方差解释（initial + extraction + rotation 三段）
    tve_rows = []
    for i in range(n_vars):
        row = {
            'component': f'Component {i + 1}',
            'initial_eigenvalue': initial_eigenvalues[i],
            'initial_variance_pct': initial_variance_explained[i],
            'initial_cumulative_pct': initial_cumulative_variance[i],
            'extraction_eigenvalue': (
                eigenvalues[i] if i < n_extracted else None
            ),
            'extraction_variance_pct': (
                variance_explained[i] if i < n_extracted else None
            ),
            'extraction_cumulative_pct': (
                cumulative_variance[i] if i < n_extracted else None
            ),
        }
        if rot_int != 1:  # 有旋转
            row.update({
                'rotation_sum_squared_loadings': (
                    rotation_sum_squared_loadings[i] if i < n_extracted else None
                ),
                'rotation_variance_pct': (
                    rotation_variance_explained[i] if i < n_extracted else None
                ),
                'rotation_cumulative_pct': (
                    rotation_cumulative_variance[i] if i < n_extracted else None
                ),
            })
        tve_rows.append(row)
    total_variance_explained = pd.DataFrame(tve_rows).set_index('component')

    # 因子载荷矩阵（取前 n_extracted 列）
    factor_matrix = pd.DataFrame(
        loadings[:, :n_extracted], index=var_idx, columns=comp_names,
    )
    if rot_int != 1:
        rotated_factor_matrix = pd.DataFrame(
            rotated_loadings[:, :n_extracted], index=var_idx, columns=comp_names,
        )
    else:
        rotated_factor_matrix = None

    if is_oblique:
        structure_matrix_df = pd.DataFrame(
            structure_matrix[:, :n_extracted], index=var_idx, columns=comp_names,
        )
        factor_corr = pd.DataFrame(
            factor_correlation_matrix[:n_extracted, :n_extracted],
            index=comp_names, columns=comp_names,
        )
    else:
        structure_matrix_df = None
        factor_corr = None

    factor_score_coeff = pd.DataFrame(
        score_coefficient_matrix[:, :n_extracted], index=var_idx, columns=comp_names,
    )
    factor_scores = pd.DataFrame(
        scores[:, :n_extracted],
        index=[f'Case {i + 1}' for i in range(n_obs)],
        columns=comp_names,
    )

    descriptive = pd.DataFrame({
        'variable': var_names,
        'mean': univariate_mean[:n_vars],
        'std_deviation': univariate_std[:n_vars],
        'n': np.full(n_vars, int(n_valid[0])),
    }).set_index('variable')

    return {
        'kmo_and_bartlett_test': kmo_bartlett,
        'communalities': communalities_df,
        'total_variance_explained': total_variance_explained,
        'factor_matrix': factor_matrix,
        'rotated_factor_matrix': rotated_factor_matrix,
        'structure_matrix': structure_matrix_df,
        'factor_score_coefficients': factor_score_coeff,
        'factor_scores': factor_scores,
        'factor_correlation_matrix': factor_corr,
        'descriptive_statistics': descriptive,
        'meta': {
            'method': 'Factor Analysis',
            'extraction_method': _EXTR_DISPLAY.get(extr_int, extr_key),
            'rotation_method': _ROT_DISPLAY.get(rot_int, rot_key),
            'score_method': _SCORE_DISPLAY.get(score_int, score_key),
            'matrix_type': mat_key,
            'n_factors_extracted': n_extracted,
            'n_factors_requested': n_factors_in,
            'n_observations': int(n_valid[0]),
            'n_variables': int(n_vars),
            'max_iter': int(max_iter),
            'is_oblique_rotation': is_oblique,
        },
    }


__all__ = ['run_factor']
