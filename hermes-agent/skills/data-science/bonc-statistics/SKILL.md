---
name: bonc-statistics
description: >
  BONC 统计分析工具集，提供 20 种统计算法，包括回归、t 检验、方差分析、描述统计、
  频率分析、自相关、交叉表、非参数检验等。采用两工具网关架构：
  propose_analysis_plan（检查数据 + 推荐方法 + 返回完整参数 Schema）和
  execute_analysis（通用算法调度器）。当用户需要进行任何统计分析时加载此技能。
version: 2.1.0
author: BONC
license: MIT
metadata:
  hermes:
    tags: [bonc, statistics, regression, anova, descriptives, data-analysis, t-test,
           correlation, frequencies, crosstabs, acf, clustering, survival]
    category: data-science
    requires_plugin: boncml-stat-tools
---

# BONC 统计分析工具（两工具架构）

本地运行的高保真统计算法引擎，20 种算法通过两工具网关架构提供。

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

## 可用算法（20 种）

| 算法名 (recommended_tool) | 分析类型 | 典型用途 |
|------|------------------|---------|
| run_regression | 线性回归 | 预测 Y、影响因素分析 |
| run_descriptives | 分组描述统计 | 分组均值/标准差 + 方差分析 |
| run_oneway | 单因素方差分析 | 多组均值比较 |
| run_ttest | t 检验 | 配对/独立/单样本均值检验 |
| run_frequencies | 频率分析 | 频率表、分布统计量 |
| run_crstab | 交叉表分析 | 交叉分类频数统计（列联表） |
| run_nptest | 非参数检验 | Mann-Whitney、Wilcoxon 等 |
| run_acf | 自相关分析 | 序列自相关性判断 |
| run_tsplot | 时间序列图 | 时序走势与基本特征 |
| run_fit | 曲线拟合 | 曲线回归拟合 |
| run_unianova | 单变量方差分析 | 多因素/协方差分析 |
| run_hiloglinear | 层次对数线性 | 分类变量关联分析 |
| run_wls | 加权最小二乘 | 异方差修正回归 |
| run_rank | 秩变换 | 排名与百分位 |
| run_kmeans | K-均值聚类 | 样本聚类分群 |
| run_sur | 生存分析 | 生存表与风险检验 |
| run_eda | 探索性分析 | 数据分布探索 |
| run_genlog | 广义对数线性 | 对数线性模型 |
| run_mresp | 多响应分析 | 多选题频率统计 |
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
3. 手动覆盖时，直接读取对应算法模块获取完整 Schema：`algorithms/<algo>.py`（如 `algorithms/ttest.py`），每个模块都包含 `schema` dict 和 `run()` 函数签名
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
