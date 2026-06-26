# 支持的统计分析能力（45 个算法）

桌面版通过图形菜单操作，AutoDL 云端版通过 `boncml <算法名> --data <数据文件> [参数]` 或 `bonc chat` 自然语言调用。

---

## 1. 描述统计与数据探索

| 能力 | CLI 命令 | 示例 |
|------|---------|------|
| 描述性统计 | `boncml eda` | `--data /root/data/eda/eda_test_data.csv --variable value` |
| 频率分析 | `boncml frequencies` | `--data /root/data/regress/case14/data.csv --variables y x1` |
| 分组描述统计 | `boncml brkdwn` | `--data /root/data/regress/case14/data.csv --dependent y --group x2` |
| 缺失值分析 | `boncml mva` | `--data /root/data/mva/case1/test_data.csv --variables var1 var2 var3` |
| 比率分析 | `boncml ratios` | `--data /root/data/ratios/data.csv --numerator value_num --denominator value_den --group group` |
| 秩变换 | `boncml rank` | `--data /root/data/rank/case1/case1.csv --variable value` |

## 2. 差异检验

| 能力 | CLI 命令 | 示例 |
|------|---------|------|
| T 检验 | `boncml ttest` | `--data /root/data/ttest/case_001.csv --test one_sample --variable x --test_value 10` |
| 单因素方差分析 | `boncml oneway` | `--data /root/data/oneway/case1/test_data.csv --dependent score --factor group --posthoc tukey` |
| 多因素方差分析 | `boncml anova` | `--data /root/data/anova/anova_data.csv --dependent score --factor method` |
| 一般线性模型 | `boncml unianova` | `--data /root/data/unianova/case32/data.csv --dependent score --factors treatment` |
| 非参数检验 | `boncml nptest` | `--data /root/data/nptest/case14/data.csv --test ks_one_sample --score age` |
| 多变量方差分析 | `boncml manova` | `--data x.csv --dependent-vars y1 y2 --design-vars group` |

## 3. 关系分析与建模

| 能力 | CLI 命令 | 示例 |
|------|---------|------|
| 交叉表与卡方检验 | `boncml crstab` | `--data /root/data/regress/case14/data.csv --row x1 --col x2` |
| 线性回归 | `boncml regress` | `--data /root/data/regress/case14/data.csv --dependent y --independents x1 x2` |
| 加权回归 | `boncml wls` | `--data /root/data/wls/case1/data.csv --dependent Y --independents X1 --source X1` |
| 广义对数线性模型 | `boncml genlog` | `--data /root/data/genlog/case1/data.csv --variables A B` |
| 分层对数线性模型 | `boncml hiloglinear` | `--data /root/data/hiloglinear/case13/data.csv --variables A B C` |
| 有序 Logistic 回归 | `boncml plum` | `--data x.csv --response-var y --covariates x1 x2` |
| 分类回归（最优量化）| `boncml catreg` | `--data x.csv --dependent y --independents x1 x2 x3` |
| 多项 Logistic 回归（无序分类）| `boncml nomreg` | `--data x.csv --target y --method-vars x1 x2 x3` |

## 4. 聚类与预测

| 能力 | CLI 命令 | 示例 |
|------|---------|------|
| K-Means 聚类 | `boncml kmeans` | `--data /root/data/2scluster/twostep2.csv --variables 身高 体重 血红蛋白 --clusters 3` |
| K 近邻分类 | `boncml knn` | `--data /root/data/knn/knn_data.csv --test /root/data/knn/knn_data.csv --target churn_risk --features age income balance` |
| 判别分析（多组分类）| `boncml dscrmn` | `--data x.csv --grouping-var g --variables v1 v2 v3` |
| 决策树（CHAID/CRT/QUEST）| `boncml dtree` | `--data x.csv --target-var y --features x1 x2` |
| 层次聚类（系统聚类）| `boncml clustr` | `--data x.csv --variables v1 v2 v3 --method ward` |

## 5. 时间序列与生存分析

| 能力 | CLI 命令 | 示例 |
|------|---------|------|
| 自相关分析 | `boncml acf` | `--data /root/data/acf/case1/data.csv --series sales --acf --maxlag 16` |
| 时间序列变换 | `boncml tsplot` | `--data /root/data/tsplot/case01/test_data.csv --variables series1` |
| 拟合误差分析 | `boncml fit` | `--data /root/data/fit/case1/data.csv` |
| 寿命表生存分析 | `boncml sur` | `--data /root/data/sur/case1/test_data.csv --time time --status status --group group` |
| Kaplan-Meier | `boncml km` | `--data /root/data/2scluster/twostep2.csv --variables 身高 体重 血红蛋白 --clusters 3` |
| Cox 比例风险回归 | `boncml coxreg` | `--data x.csv --time-var t --event-var e --covariates x1 x2` |
| 指数平滑/曲线拟合（时序）| `boncml extrap` | `--data x.csv --y-var y --method curvefit --x-var x` |
| 谱分析（周期图/谱密度，频域）| `boncml spctrl` | `--data x.csv --series sales --window tukey` |

## 6. 问卷与实验设计

| 能力 | CLI 命令 | 示例 |
|------|---------|------|
| 多重响应分析 | `boncml mresp` | `--data /root/data/mresp/case1/data.csv --responses v1 v2 v3 --counted_value 1` |
| 正交设计 | `boncml market` | `--data /root/data/mva/case1/test_data.csv --method orthoplan --factors "price:low,high"` |
| 信度分析（Cronbach α/ICC/ANOVA）| `boncml reliab` | `--data x.csv --variables item1 item2 item3 item4` |

## 7. 相关分析、降维与诊断评估

| 能力 | CLI 命令 | 示例 |
|------|---------|------|
| 皮尔逊相关分析 | `boncml pearson` | `--data  --variables anxiety depression stress` |
| Spearman/Kendall 等级相关 | `boncml spearman` | `--data  --variables v1 v2 [--coefficient kendall]` |
| 偏相关分析 | `boncml partial` | `--data  --main anxiety depression --control stress` |
| 因子分析 / 主成分分析 | `boncml factor` | `--data  --pca --rotate varimax --n-factors 2` |
| 邻近度矩阵（距离/相似度）| `boncml distance` | `--data  --measure euclidean --between cases` |
| ROC 曲线分析 | `boncml roc` | `--data  --state status --positive pos --test marker1 marker2` |
| 分类主成分分析（最优量化 PCA）| `boncml catpca` | `--data x.csv --variables v1 v2 v3 v4 --n-components 2` |
| 多重对应分析 | `boncml homals` | `--data x.csv --variables v1 v2 v3 --ndim 2` |
| 非线性典型相关（多集合）| `boncml overal` | `--data x.csv --set v1 v2 --set v3 v4 --n-dimensions 2` |
