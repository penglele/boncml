# BONCML — 统计分析 Agent

BONCML 是一个基于 AI Agent 的统计分析系统，提供 26 个 SPSS 兼容统计算法，支持自然语言驱动的数据分析。

## 功能

- **26 个统计算法**: t 检验、方差分析、回归、聚类、频数分析等
- **自然语言交互**: 用中文描述分析需求，Agent 自动选择算法并执行
- **语义检索**: BGE-M3 模型匹配用户问题到最佳算法
- **源码保护**: 所有业务逻辑均为 Nuitka/Fortran 编译的 .so 二进制

## 包含组件

| 组件 | 说明 |
|------|------|
| Hermes Agent | AI Agent 框架 (Nuitka 编译) |
| boncml-stat-tools | 统计分析插件 (26 算法) |
| bge-m3 | 语义检索模型 (1024 维) |

## 使用方法

### AutoDL 一键部署

在本镜像创建实例后:

```bash
# 1. 配置 LLM API Key
cat > /root/.hermes/config.yaml << 'EOF'
model:
  provider: zai
  name: glm-5.1
  base_url: https://open.bigmodel.cn/api/coding/paas/v4
  api_key: 你的API_KEY
EOF

# 2. 准备数据 (上传到 /root/data/)
mkdir -p /root/data

# 3. 开始分析
bonc chat -q "对 /root/data/my_data.csv 做描述性统计分析" --yolo
```

### CLI 示例

```bash
# 查看已注册插件
bonc plugins list

# 单样本 t 检验
bonc chat -q "对 data.csv 的 x 列做单样本t检验，检验均值是否等于10" --yolo

# 单因素方差分析
bonc chat -q "对 data.csv 的 score 按 group 分组做方差分析" --yolo

# 多元回归
bonc chat -q "对 data.csv 做 y 对 x1 x2 x3 的多元回归" --yolo
```

### Python API

```python
import sys
sys.path.insert(0, '/root/boncml-stat-tools')

from boncml._core import _get_runtime_root
from boncml._plan import _run_propose_analysis_plan

# 语义检索推荐算法
result = _run_propose_analysis_plan({
    'data_path': '/root/data/my_data.csv',
    'research_question': '比较两组数据的均值差异'
}, _get_runtime_root()[0])

print(result['recommended_tool'])
```

## 系统要求

- Python 3.11 (所有 .so 编译于 cpython-311)
- Linux x86_64
- 磁盘: >= 30G (含模型和依赖)
- 内存: >= 8G

## 技术架构

```
用户 → Hermes Agent (LLM) → propose_analysis_plan → 语义检索 + 规则精排
                           → execute_analysis → algorithms/*.so → vendored/*.so (Fortran)
```

## 源码保护

| 组件 | 保护方式 |
|------|---------|
| boncml 核心引擎 | Nuitka → .so |
| boncml 算法 (26个) | Nuitka → .so |
| vendored Fortran | 编译 → .so |
| Hermes 框架 | Nuitka → .so (227个) |
