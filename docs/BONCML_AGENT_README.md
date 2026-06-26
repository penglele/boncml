# BONCML AI 统计分析 Agent（AutoDL 云端版）

用自然语言完成 SPSS 兼容统计分析。

BONCML 是一个面向科研、教学和数据分析场景的 AI 统计分析 Agent。
用户只需上传 CSV、TSV、Excel 或 SPSS `.sav` 数据文件，并用自然语言描述分析需求，系统即可自动读取数据、识别变量类型、推荐统计方法，并执行 t 检验、方差分析、回归、卡方检验、非参数检验、相关分析、因子分析、聚类、生存分析、ROC 曲线等 31 类常用统计分析。

## 核心特点

- **自然语言交互** — 直接描述分析需求，无需记忆复杂参数
- **SPSS 兼容工具集** — 覆盖科研与教学中常用的统计分析方法
- **自动推荐分析方法** — 根据数据结构和用户问题推荐合适算法
- **支持多种数据格式** — CSV、TSV、Excel、SPSS `.sav`
- **无 GPU 要求** — 统计计算基于 CPU，适合低成本部署
- **适合中文场景** — 支持中文自然语言描述统计需求

## BONCML 和普通大模型对话有什么不同？

| | 普通大模型 | BONCML |
|--|-----------|--------|
| 统计分析 | 只能给统计建议 | 实际读取数据并执行分析 |
| 结果质量 | 容易给出泛泛解释 | 调用确定的统计工具计算结果 |
| 数据理解 | 不一定知道数据结构 | 自动识别变量类型和数据格式 |
| 可复现性 | 结果难以复现 | 基于工具链执行，流程可追踪 |
| 方法选择 | 需要用户自己判断 | 可根据语义检索推荐合适算法 |
| SPSS 兼容 | 不兼容 | 支持 `.sav` 文件和 SPSS 风格统计工具 |

## Agent 分析流程

用户只需提出自然语言问题，BONCML 自动完成三步分析：

```
用户提问
  → inspect_dataset：自动读取数据，识别变量类型
  → propose_analysis_plan：推荐合适的统计分析方法
  → execute_analysis：执行算法并返回统计结果与结论
```

这意味着用户不需要一开始就知道应该选择 t 检验、方差分析、卡方检验还是非参数检验，系统会根据数据和问题辅助判断。

## 你可以这样使用

以下示例均可直接在镜像环境中运行（数据文件已内置），同时给出自然语言和 CLI 两种用法。

### T 检验

检验产品重量均值是否等于标称值 10g。

```bash
# 自然语言
bonc chat -q "对 /root/data/ttest/case_001.csv 做单样本 t 检验，检验变量 x 的均值是否等于 10" --yolo

# CLI 等价命令
boncml ttest --data /root/data/ttest/case_001.csv --test one_sample --variable x --test_value 10
```

### 单因素方差分析

检验三种处理组的成绩是否存在显著差异。

```bash
# 自然语言
bonc chat -q "对 /root/data/oneway/case1/test_data.csv 做单因素方差分析，因变量 score，分组变量 group，用 Tukey 做事后检验" --yolo

# CLI 等价命令
boncml oneway --data /root/data/oneway/case1/test_data.csv --dependent score --factor group --posthoc tukey --statistics  descriptive homogeneity
```

### 多元线性回归

分析广告投入和定价对销售额的影响。

```bash
# 自然语言
bonc chat -q "对 /root/data/regress/case14/data.csv 做多元线性回归，因变量 y，自变量 x1 和 x2" --yolo

# CLI 等价命令
boncml regress --data /root/data/regress/case14/data.csv --dependent y --independents x1 x2 --statistics CI ZPP TOL DESCRIPTIVES DW
```

### 交叉表分析

分析广告投入和定价的交叉频数分布。将两个分类变量进行交叉制表，观察各组合的频数，判断是否存在关联

```bash
# 自然语言
bonc chat -q "对 /root/data/regress/case14/data.csv 做交叉表分析，行变量 x1，列变量 x2，并进行卡方检验" --yolo

# CLI 等价命令
boncml crstab --data /root/data/crstab/test_cases_enhanced.csv --row row_var --col col_var --cells count expected row_pct column_pct total_pct
```

### 探索性分析

快速了解数据分布特征（均值、偏度、峰度、正态性、离群值）。

```bash
# 自然语言
bonc chat -q "对 /root/data/eda/eda_test_data.csv 的 value 列做探索性分析" --yolo

# CLI 等价命令
boncml eda --data /root/data/eda/eda_test_data.csv --variable value --factor group --calculate_levene
```

### 频率分析

查看变量的频数分布。

```bash
# 自然语言
bonc chat -q "对 /root/data/frequencies/case1/test_data.csv 的 score 和 age_group 列做频率分析" --yolo

# CLI 等价命令
boncml frequencies --data /root/data/frequencies/case1/test_data.csv --variables score age_group --statistics mean std_dev min max skewness kurtosis median variance se_mean range
```

### K-Means 聚类

将患者按生理指标分群。

```bash
# 自然语言
bonc chat -q "对 /root/data/kmeans_pilot/kmeans_data.csv 做 K-Means 聚类，聚类变量为 V1 V2 V3，分为 4 组" --yolo

# CLI 等价命令
boncml kmeans --data /root/data/kmeans_pilot/kmeans_data.csv --variables V1 V2 V3 --clusters 4
```

### 寿命表生存分析

比较两组患者的生存情况。

```bash
# 自然语言
bonc chat -q "对 /root/data/sur/case1/test_data.csv 做寿命表生存分析，时间变量 time，状态变量 status，分组变量 group" --yolo

# CLI 等价命令
boncml sur --data /root/data/sur/case1/test_data.csv --time time --status status --group group --interval_thru 20 --interval_by 2
```

### 多重响应分析

分析问卷多选题的回答分布。

```bash
# 自然语言
bonc chat -q "对 /root/data/mresp/case1/data.csv 做多重响应分析，响应变量 v1 v2 v3，计数值为 1" --yolo

# CLI 等价命令
boncml mresp --data /root/data/mresp/case1/data.csv --responses v1 v2 v3 --counted_value 1
```

### 自相关分析

分析销售额时间序列的自相关结构。

```bash
# 自然语言
bonc chat -q "对 /root/data/acf/case1/data.csv 做自相关分析，序列变量 sales，最大滞后 16" --yolo

# CLI 等价命令
boncml acf --data /root/data/acf/case1/data.csv --series sales --acf --maxlag 16
```

### 皮尔逊相关分析

衡量多个连续变量之间的线性关联程度。

```bash
# 自然语言
bonc chat -q "对 /root/data/boncml-test/factor/factor_data.csv 的 anxiety depression stress 三列做皮尔逊相关分析" --yolo

# CLI 等价命令
boncml pearson --data /root/data/boncml-test/factor/factor_data.csv --variables anxiety depression stress
```

### 因子分析 / 主成分分析（PCA）

从多个相关变量中提取少数潜在因子实现降维，支持 7 种提取法、6 种旋转、3 种得分法。

```bash
# 自然语言
bonc chat -q "对 /root/data/boncml-test/factor/factor_data.csv 的 high_corr_var1 到 high_corr_var5 做主成分分析，Varimax 旋转，提取 2 个主成分" --yolo

# CLI 等价命令
boncml factor --data /root/data/boncml-test/factor/factor_data.csv \
  --variables high_corr_var1 high_corr_var2 high_corr_var3 high_corr_var4 high_corr_var5 \
  --pca --rotate varimax --n-factors 2
```

### ROC 曲线分析

评估诊断标记物区分阳性/阴性的判别能力，输出 AUC、灵敏度/特异度、最佳截断值。

```bash
# 自然语言
bonc chat -q "用 ROC 曲线评估 /root/data/boncml-test/roc_demo.csv 中 marker1 和 marker2 区分 status(pos/neg) 的诊断能力，阳性定义为 pos" --yolo

# CLI 等价命令
boncml roc --data /root/data/boncml-test/roc_demo.csv --state status --positive pos --test marker1 marker2
```

## 输出结果示例

用户输入：

```bash
bonc chat -q "对 /root/data/ttest/case_001.csv 做单样本 t 检验，检验变量 x 的均值是否等于 10" --yolo
```

系统输出：

```text
单样本 t 检验结果（检验变量 x 的均值是否等于 10）

描述统计
- N = 10
- Mean = 14.5
- Std. Deviation = 3.0277
- Std. Error Mean = 0.9574

检验结果
- Test Value = 10
- t = 4.7001
- df = 9
- Sig. (2-tailed) = 0.0011
- Mean Difference = 4.5000
- 95% CI [2.3341, 6.6659]

结论：在 α = 0.05 的显著性水平下，p = 0.0011 < 0.05，拒绝原假设。
变量 x 的总体均值显著不等于 10，样本均值 14.5 高于检验值。
```

## 为什么在 AutoDL 上运行 BONCML？

- 无需本地配置复杂统计环境
- 不依赖 GPU，CPU 环境即可运行，成本更低
- 支持上传数据文件后直接分析
- 镜像环境已预装核心依赖
- 适合教学演示、科研复现实验和临时数据分析任务
- 可结合不同 LLM API 使用

## 基本环境

| 项目 | 说明 |
|------|------|
| 框架 | Python 3.11 / Nuitka 编译 / Hermes Agent v0.8.0 |
| GPU | 无 GPU 要求 |
| 计算方式 | 统计算法使用 CPU |
| Embedding | CPU 版 PyTorch |
| LLM 模型 | 支持 GLM-5.1 等国内外模型 |
| 算法数量 | 31 个 SPSS 兼容统计算法 |

## 快速开始

### 1. Clone 代码

```bash
cd /root
git clone https://github.com/penglele/boncml.git
```

### 2. 配置 LLM API Key

支持国内外主流模型，以智谱为例：

```bash
cat > /root/.hermes/.env << 'EOF'
  GLM_API_KEY=<替换为你的 API_KEY>
  GLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4
EOF
```

### 3. 验证环境

```bash
export PATH=$PATH:/root/.local/bin

# 验证插件加载
bonc plugins list

# 验证语义检索
bonc chat -q "对数据做t检验" --yolo
```

### 4. 准备数据

```bash
mkdir -p /root/data
# 通过 scp 或 AutoDL 文件管理器上传数据到 /root/data/
```

将你的数据文件（CSV / TSV / XLSX / SAV）上传到 `/root/data/`。

### 5. 执行分析

```bash
bonc chat -q "对 /root/data/test.csv 的收入列做描述性统计" --yolo
```

## 常用运维命令

```bash
# 查看服务状态
bonc gateway status

# 重启服务
bonc gateway restart

# 查看插件列表
bonc plugins list

# 查看已注册工具
bonc tools list
```

## 常见问题

**Q: 我不会 Python，可以使用吗？**
可以。BONCML 支持自然语言交互，只需要描述分析需求，例如"比较三组成绩是否有显著差异"，系统会自动推荐并执行合适的统计方法。

**Q: 它能替代 SPSS 吗？**
BONCML 提供 31 个 SPSS 兼容统计工具，适合完成常见统计分析任务。对于高度复杂的 SPSS 工作流，建议结合人工检查和专业统计判断。

**Q: 它会自动选择统计方法吗？**
会。系统会先读取数据并识别变量类型，再通过语义检索推荐合适的统计算法，然后执行分析。

**Q: 支持 SPSS 的 `.sav` 文件吗？**
支持。BONCML 支持 `.sav` 数据文件，并尽量保留变量标签，适合已有 SPSS 数据用户迁移使用。

**Q: 是否需要 GPU？**
不需要。BONCML 的统计计算使用 CPU，embedding 使用 CPU 版 PyTorch，适合低成本运行。

**Q: 结果是否可以用于论文？**
可以作为统计分析辅助工具使用，但论文发表前仍建议研究者核对数据、参数、统计假设和结果解释。

**Q: 提示 "API Key 无效"**
检查 `config.yaml` 中的 api_key 是否正确，确保模型账户有余额。

**Q: 提示 "runtime assets missing"**
确认 `/root/boncml-stat-tools/vendored/` 目录存在且包含 `.so` 文件。

**Q: 分析结果报参数错误**
LLM 可能传了错误的参数名，系统有 alias 容错机制自动纠正。如仍然失败，尝试在提问中更明确地指定参数（如"检验值等于10"、"置信水平95%"）。

**Q: Excel 文件读取失败**
vendored 环境可能缺少 openpyxl，LLM 会自动降级用 Python scipy 完成分析。建议优先使用 CSV 格式。
