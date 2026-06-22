---
name: bonc-statistics
description: >
  BONC 统计分析工具集，提供 45 种统计算法，包括回归、t 检验、方差分析、描述统计、
  频率分析、自相关、交叉表、非参数检验、聚类、生存分析、相关分析、因子分析、
  ROC 曲线、距离矩阵、Cox 比例风险回归、判别分析、决策树、有序/多项 Logistic
  回归、信度分析、多变量方差分析、分类主成分/回归、层次聚类、对应分析、典型
  相关、时序曲线拟合、谱分析等。采用两工具网关架构：
  propose_analysis_plan（检查数据 + 推荐方法 + 返回完整参数 Schema）和
  execute_analysis（通用算法调度器）。当用户需要进行任何统计分析时加载此技能。
version: 2.3.0
author: BONC
license: MIT
metadata:
  hermes:
    tags: [bonc, statistics, regression, anova, descriptives, data-analysis, t-test,
           correlation, frequencies, crosstabs, acf, clustering, survival,
           pearson, spearman, partial-correlation, factor-analysis, roc, distance,
           dimensionality-reduction, diagnostic,
           cox-regression, discriminant-analysis, decision-tree,
           ordinal-logistic, multinomial-logistic, reliability, manova,
           catpca, hierarchical-clustering, correspondence-analysis,
           canonical-correlation, curve-fitting, spectral-analysis]
    category: data-science
    requires_plugin: boncml-stat-tools
---

# BONC 统计分析工具（两工具架构）

本地运行的高保真统计算法引擎，45 种算法通过两工具网关架构提供。

## 工作流（必须按此顺序）

1. **调用 `propose_analysis_plan`**，传入 data_path + research_question
   - 返回：数据集概况、推荐工具名、置信度、**完整参数 Schema**
2. **调用 `execute_analysis`**，传入 algo_name + params（根据步骤 1 返回的 Schema 填写）
   - 不要猜测参数——必须先调用 propose_analysis_plan 获取完整参数定义

## 工具参考

### `propose_analysis_plan`（必须先调用）
```json
{
  "data_path": "/absolute/path/to/data.csv",
  "research_question": "描述你的研究问题，例如：X对Y有什么影响？两组之间有差异吗？",
  "variables": ["可选：指定关注的变量名"]
}
```
返回：数据集摘要（行数/列数/类型）、推荐工具名、置信度、推荐工具的**完整 JSON Schema**。

### `execute_analysis`（propose 之后调用）
```json
{
  "algo_name": "propose_analysis_plan 返回的 recommended_tool 字段值",
  "params": {
    "data_path": "/absolute/path/to/data.csv",
    "... 根据 propose 返回的 tool_schema 填写其他参数 ..."
  }
}
```

## 可用算法（45 种）

| 算法名 (recommended_tool) | 分析类型 | 典型用途 |
|------|------------------|---------|
| run_regression | 线性回归 | 预测 Y、影响因素分析 |
| run_descriptives | 分组描述统计 | 分组均值/标准差 + 方差分析 |
| run_oneway | 单因素方差分析 | 多组均值比较 |
| run_anova | 多因素方差分析 | 多因子/协方差分析 |
| run_ttest | t 检验 | 配对/独立/单样本均值检验 |
| run_frequencies | 频率分析 | 频率表、分布统计量 |
| run_crstab | 交叉表分析 | 交叉分类频数统计（列联表） |
| run_nptest | 非参数检验 | Mann-Whitney、Wilcoxon 等 |
| run_acf | 自相关分析 | 序列自相关性判断 |
| run_tsplot | 时间序列图 | 时序走势与基本特征 |
| run_fit | 曲线拟合 | 曲线回归拟合 |
| run_unianova | 单变量方差分析 | 多因素/协方差分析 |
| run_hiloglinear | 层次对数线性 | 分类变量关联分析 |
| run_genlog | 广义对数线性 | 对数线性模型 |
| run_wls | 加权最小二乘 | 异方差修正回归 |
| run_rank | 秩变换 | 排名与百分位 |
| run_kmeans | K-均值聚类 | 样本聚类分群 |
| run_knn | K 近邻分类 | 样本分类预测 |
| run_sur | 生存分析 | 生存表与风险检验 |
| run_km | Kaplan-Meier | 生存曲线估计 |
| run_eda | 探索性分析 | 数据分布探索 |
| run_mresp | 多响应分析 | 多选题频率统计 |
| run_mva | 缺失值分析 | 缺失模式与统计 |
| run_ratios | 比率分析 | 分组比率统计 |
| run_market | 正交设计 | 实验设计与正交表 |
| run_pearson | 皮尔逊相关 | 双变量线性相关 + 显著性 |
| run_spearman | 斯皮尔曼秩相关 | 非参数秩相关（含 Kendall tau-b） |
| run_partial | 偏相关 | 控制混杂变量后的净相关 |
| run_factor | 因子分析 | 主成分提取 / 降维 / KMO-Bartlett |
| run_roc | ROC 曲线 | 二分类诊断 / 阈值评估 / AUC |
| run_distance | 距离矩阵 | 个案或变量间邻近度（聚类输入） |
| run_coxreg | Cox 比例风险回归 | 生存分析（带协变量的风险模型） |
| run_dscrmn | 判别分析 | 多组线性分类、典型判别函数 |
| run_dtree | 决策树 | CHAID/CRT/QUEST 分类树 |
| run_plum | 有序 Logistic 回归 | 有序等级因变量回归（PLUM） |
| run_reliab | 信度分析 | Cronbach α / ICC / 重复测量方差 |
| run_manova | 多变量方差分析 | 多因变量多元检验（Pillai/Wilks/Hotelling/Roy） |
| run_catpca | 分类主成分分析 | 类别变量最优量化 PCA |
| run_catreg | 分类回归 | 混合尺度（名义/有序/连续）变量回归 |
| run_clustr | 层次聚类 | Ward/平均/最远 系统聚类 + 簇归属 |
| run_homals | 多重对应分析 | 名义变量同质性分析、类别量化 |
| run_overal | 非线性典型相关 | 多变量集合的典型相关（OVERALS） |
| run_extrap | 时序曲线拟合/指数平滑 | 趋势曲线（线性/二次/指数…）+ 平滑预测 |
| run_spctrl | 谱分析 | 频域周期图 + 谱密度（SPECTRA） |
| run_nomreg | 多项 Logistic 回归 | 无序分类因变量回归（NOMREG） |
| inspect_dataset | 数据集检视 | 列信息与基本统计（propose 内部调用） |

## 环境要求

- 插件配置：`~/.hermes/plugins/boncml-stat-tools/config.yaml`
  - `python_path` 须指向包含 numpy/pandas 的 conda 环境
- 算法运行时通过子进程桥接（`bridge_runner.py`）使用配置的 Python 执行

## Propose 低置信度时的处理策略

`propose_analysis_plan` 依赖语义检索（bge-m3），当用户意图非常明确但检索词不匹配时会推荐错误工具（如用户说"单样本t检验"却被推荐 `run_descriptives`，置信度仅 0.38）。

**处理流程**：
1. 先调用 propose 获取推荐，检查 `confidence` 字段
2. 若 confidence < 0.6 或推荐工具明显不符用户意图 → **根据领域知识手动覆盖**
3. 手动覆盖时，**不要读 `algorithms/<algo>.py`**（生产环境是 Cython .so 部署，没有 .py 源码，读了会报错）。改用 `propose_analysis_plan` 返回结果里的 `tool_schemas` 字段——它已包含候选工具的完整 JSON Schema；或在 research_question 里**明确算法类型**（如"层次聚类""Ward"而非泛"聚类"），让检索重新命中正确工具
4. 参数填写仍须参照 Schema 中的 `required` 和 `properties`，不可猜测

## 故障排除

| 问题 | 解决方案 |
|-------|----------|
| `algos_repo_path is not configured` | 不再需要此配置项（已使用 vendored 资产） |
| `No module named 'pandas'` | 在 `python_path` 指向的环境中安装：`pip install pandas` |
| `No module named 'numpy'` | 在 `python_path` 指向的环境中安装：`pip install numpy` |
| `Unable to locate .so module` | 编译：`conda activate spss-fortran && make ALGO=<name>` |
| 工具返回错误 | 查看日志：`~/.hermes/logs/agent.log` |
| `execute_analysis` 报 missing_column 如 `interval_thru` | `run_sur` 需要 `interval_thru` 和 `interval_by`（在 tool_schema 的 `required` 中），从 propose 返回的 Schema 读取完整参数 |
| propose 返回结果被截断（过大） | 结果自动保存到临时文件，用 read_file 读取完整内容 |
| 无法直接 json.loads 从 propose 结果提取 Schema | Schema JSON 使用转义字符（`\\n`/`\\\"`），需要 unescape：`schema_str.encode().decode('unicode_escape')` 再 json.loads |
| bridge_runner.py 找不到 | 实际路径在插件子目录：`<plugin_root>/boncml/bridge_runner.py`，不是插件根目录 |
| propose 推荐了明显错误的工具 | 语义检索可能不匹配明确意图。检查 confidence < 0.6 时，直接读 `algorithms/<algo>.py` 中的 schema 手动覆盖 |
