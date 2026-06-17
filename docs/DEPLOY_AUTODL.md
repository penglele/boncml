# AutoDL 商业化部署手册（无源码 Cython .so 模式）

适用场景：将 `boncml-stat-tools` 部署到 AutoDL（或任何 Ubuntu 22.04 / glibc 2.35+ 服务器）作为商业镜像交付，**所有 Python 源码 Cython 编译为 `.so`，不向客户暴露 .py**。

本文档基于 2026-06-16 在 AutoDL 实例 `connect.weste.seetacloud.com:11035`（Ubuntu 22.04, glibc 2.35）的实战部署流程，覆盖**新增算法**的完整步骤。

---

## 1. 服务器环境前提

| 项目 | 要求 |
|------|------|
| OS | Ubuntu 22.04+（glibc ≥ 2.35） |
| Hermes Agent | 已安装，venv 路径 `/root/.hermes/hermes-agent/venv/`（Python **3.11**） |
| Cython | 已在 Hermes venv 安装：`/root/.hermes/hermes-agent/venv/bin/pip install Cython numpy` |
| gcc | 系统自带（`x86_64-linux-gnu-gcc`） |
| Fortran 编译能力 | 可选，仅当需要重编 vendored/lib/*.so 时才需要 `gfortran` |

> 与阿里云 39.100.67.26 的差异：那台 glibc 2.32 低于编译阈值，必须用 `.py` 源码部署；AutoDL glibc 2.35 兼容 Cython 编译产物，可走完整 `.so` 商业化模式。

---

## 2. 部署架构（最终形态）

```
/usr/local/bin/boncml                              ← CLI 入口 wrapper
  └─ exec /root/.hermes/hermes-agent/venv/bin/python -m boncml_cli.main

/root/.hermes/plugins/boncml-statistics            ← Hermes 插件入口（软链）
  └─ → /root/boncml-stat-tools

/root/boncml-stat-tools/                           ← 唯一代码库（编译产物）
├── __init__.cpython-311-*.so                      ← register() 编译产物
├── __init__.py                                    ← 8 行引导，加载上述 .so
├── plugin.yaml / config.yaml / tools_meta.yaml   ← 配置文件（保留 .yaml）
├── boncml/
│   ├── __init__.py                                ← 包入口（保留 .py，注入 sys.path）
│   ├── _core/_plan/_registry/_schemas/_dynamic/_compat/bridge_runner.cpython-311-*.so
│   └── algorithms/
│       ├── _base.cpython-311-*.so                 ← 协议定义（编译产物）
│       └── <algo>.cpython-311-*.so                ← 每个算法一个 .so
├── boncml_cli/
│   ├── __init__.py                                ← 保留 .py
│   ├── main.py                                    ← CLI -m 入口（保留 .py）
│   └── algo_specs.cpython-311-*.so                ← CLI subcommand 注册表
├── retrieval/
│   └── _engine.cpython-311-*.so                   ← bge-m3 检索引擎
├── vendored/
│   ├── src/spss_api/<algo>/{__init__.py, api.py}  ← API 层（保留 .py）
│   └── lib/linux_x86_64/*.cpython-311-*.so        ← Fortran/pandas 计算内核
└── docs/ tools_meta.yaml retrieval/*.yaml
```

**保留 `.py` 的文件**（运行入口 / 配置 / 协议定义）：
- 顶层 `__init__.py`（8 行 .so 引导）
- `boncml/__init__.py`（包初始化 + sys.path 注入）
- `boncml_cli/__init__.py` + `boncml_cli/main.py`（CLI `-m` 入口）
- `vendored/src/spss_api/*/__init__.py` + `api.py`（算法 API 层）
- 所有 `*.yaml` / `*.json` 配置文件

**编译为 `.so` 的文件**（核心业务逻辑）：
- `boncml/_core.py` / `_plan.py` / `_registry.py` / `_schemas.py` / `_dynamic.py` / `_compat.py` / `bridge_runner.py`
- `boncml/algorithms/*.py`（除 `_base.py`，按需要决定是否编译）
- `boncml_cli/algo_specs.py`
- `retrieval/_engine.py`

---

## 3. 一次性配置（首次部署）

只需做一次，后续更新代码不再重复。

```bash
# 1. 在 Hermes venv 装 Cython + numpy（如未装）
/root/.hermes/hermes-agent/venv/bin/pip install Cython numpy

# 2. 创建 CLI wrapper（如不存在）
cat > /usr/local/bin/boncml <<'EOF'
#!/bin/bash
PYTHONPATH="/root/boncml-stat-tools" \
exec /root/.hermes/hermes-agent/venv/bin/python -m boncml_cli.main "$@"
EOF
chmod +x /usr/local/bin/boncml

# 3. 创建 Hermes 插件软链（如不存在）
mkdir -p /root/.hermes/plugins
ln -sfn /root/boncml-stat-tools /root/.hermes/plugins/boncml-stat-tools

# 4. 创建 bonc 包装器（如不存在）
cat > /root/.local/bin/bonc <<'EOF'
#!/bin/bash
HERMES=/root/.hermes/hermes-agent/venv/bin/hermes
case "$1" in
  chat)       exec $HERMES "$@" --quiet ;;
  "")         exec $HERMES chat --quiet ;;
  *)          exec $HERMES "$@" ;;
esac
EOF
chmod +x /root/.local/bin/bonc
```

---

## 4. 新增算法部署 SOP

> 以新增 6 个算法（distance / factor / partial / pearson / roc / spearman）为例。
> 替换 `<NEW_ALGO>` 为实际算法名即可推广到任意新算法。

### Step 1：本地准备清单

部署前确认本地仓库以下文件齐全：

| 文件 | 路径 | 必须 |
|------|------|------|
| 算法模块源码 | `boncml/algorithms/<NEW_ALGO>.py` | ✅ |
| 算法 API | `vendored/src/spss_api/<NEW_ALGO>/{__init__.py, api.py}` | ✅ |
| Fortran/pandas 内核 | `vendored/lib/linux_x86_64/<NEW_ALGO>.cpython-311-x86_64-linux-gnu.so` | ✅（如有 Fortran 源） |
| CLI 参数 spec | `boncml_cli/algo_specs.py`（在 SPECS dict 里加新算法条目） | ✅ |
| 检索文本 | `tools_meta.yaml`（加 `run_<NEW_ALGO>: "..."`） | ✅ |
| Hermes skill | `boncml/hermes-agent/skills/data-science/bonc-statistics/SKILL.md`（更新算法表） | ✅ |

如 Fortran 内核 .so 缺失，需先在能编译的环境编译：
```bash
cd /root/spss-algos-transplant  # 或任何有 gfortran 的服务器
make library ALGO=<NEW_ALGO>
cp lib/<NEW_ALGO>_fortran.cpython-311-x86_64-linux-gnu.so \
   vendored/lib/linux_x86_64/
```

### Step 2：上传 vendored 资产（保留 .py）

```bash
cd <本地 boncml-stat-tools 仓库根>

# 2.1 算法 API 目录（保留 .py，运行时由算法模块加载）
scp -P 11035 -r vendored/src/spss_api/<NEW_ALGO> \
    root@connect.weste.seetacloud.com:/root/boncml-stat-tools/vendored/src/spss_api/

# 2.2 Fortran/pandas 计算内核 .so
scp -P 11035 \
    vendored/lib/linux_x86_64/<NEW_ALGO>.cpython-311-x86_64-linux-gnu.so \
    root@connect.weste.seetacloud.com:/root/boncml-stat-tools/vendored/lib/linux_x86_64/

# 2.3 更新 tools_meta.yaml（检索文本）
scp -P 11035 tools_meta.yaml \
    root@connect.weste.seetacloud.com:/root/boncml-stat-tools/
```

### Step 3：Cython 编译算法模块（关键，含包路径坑）

> ⚠️ **必须用完整包路径 `boncml.algorithms.<NEW_ALGO>`**，不能用顶层 `<NEW_ALGO>`。
> 原因见下方「[已知坑](#5-已知坑与排错)」。

```bash
# 3.1 在服务器临时目录搭建包结构
ssh -P 11035 root@connect.weste.seetacloud.com '
  mkdir -p /tmp/rebuild/boncml/algorithms
  touch /tmp/rebuild/boncml/__init__.py /tmp/rebuild/boncml/algorithms/__init__.py
'

# 3.2 上传算法源码到包结构里（保持 .py 文件名）
scp -P 11035 boncml/algorithms/<NEW_ALGO>.py \
    root@connect.weste.seetacloud.com:/tmp/rebuild/boncml/algorithms/

# 3.3 服务器上 Cython 编译（用 Hermes venv Python 3.11）
ssh -P 11035 root@connect.weste.seetacloud.com '
  PY=/root/.hermes/hermes-agent/venv/bin/python
  cd /tmp/rebuild
  cat > setup.py <<EOF
from setuptools import setup, Extension
from Cython.Build import cythonize
exts = [Extension("boncml.algorithms.<NEW_ALGO>", ["boncml/algorithms/<NEW_ALGO>.py"])]
setup(
    name="boncml_algo_rebuild",
    ext_modules=cythonize(exts, language_level=3,
        compiler_directives={"embedsignature": True, "binding": True}),
)
EOF
  $PY setup.py build_ext --inplace 2>&1 | tail -5
  ls -la /tmp/rebuild/boncml/algorithms/*.so
'
```

### Step 4：替换 .so，删除 .py / .c（商业化）

```bash
ssh -P 11035 root@connect.weste.seetacloud.com '
  # 备份现有 .so（可选，便于回滚）
  cp /root/boncml-stat-tools/boncml/algorithms/<NEW_ALGO>.cpython-311-*.so \
     /tmp/<NEW_ALGO>.so.bak 2>/dev/null || true

  # 替换为新编译 .so
  cp /tmp/rebuild/boncml/algorithms/<NEW_ALGO>.cpython-311-x86_64-linux-gnu.so \
     /root/boncml-stat-tools/boncml/algorithms/

  # 清理临时目录
  rm -rf /tmp/rebuild

  # 确认 algorithms/ 目录无 .py / .c 残留
  ls /root/boncml-stat-tools/boncml/algorithms/*.py 2>&1
  ls /root/boncml-stat-tools/boncml/algorithms/*.c 2>&1
'
```

### Step 5：同步 algo_specs.so（CLI subcommand 注册）

如果新增算法要让 `boncml <NEW_ALGO>` 子命令可用，必须重编 `algo_specs.so`：

```bash
# 上传最新 algo_specs.py
scp -P 11035 boncml_cli/algo_specs.py root@connect.weste.seetacloud.com:/tmp/

ssh -P 11035 root@connect.weste.seetacloud.com '
  PY=/root/.hermes/hermes-agent/venv/bin/python
  cd /tmp
  cat > setup_specs.py <<EOF
from setuptools import setup, Extension
from Cython.Build import cythonize
setup(
    name="algo_specs_rebuild",
    ext_modules=cythonize(
        [Extension("algo_specs", ["algo_specs.py"])],
        language_level=3,
        compiler_directives={"embedsignature": True, "binding": True},
    ),
)
EOF
  $PY setup_specs.py build_ext --inplace 2>&1 | tail -3

  # 替换
  cp /tmp/algo_specs.cpython-311-x86_64-linux-gnu.so \
     /root/boncml-stat-tools/boncml_cli/algo_specs.cpython-311-x86_64-linux-gnu.so

  # 清理
  rm -f /tmp/algo_specs.py /tmp/algo_specs.c /tmp/setup_specs.py
  rm -rf /tmp/build

  # 验证 subcommand 已注册
  boncml --help 2>&1 | head -3
'
```

### Step 6：同步 Hermes Skill

```bash
# 部署仓库改完后，推送到服务器
scp -P 11035 \
    /Users/penglei/Desktop/JApplication/work_space/git_clone/boncml/hermes-agent/skills/data-science/bonc-statistics/SKILL.md \
    root@connect.weste.seetacloud.com:/root/.hermes/skills/data-science/bonc-statistics/SKILL.md
```

**SKILL.md 改动要点**（新增算法时必做）：
- description 头部数字 +1（如 `25 种` → `31 种`）
- 算法表标题数字同步
- 算法表末尾加新算法行（在 `inspect_dataset` 之前）
- tags 数组加入相关领域标签
- version 号递增

### Step 7：重启 Hermes（让 skill 生效）

```bash
ssh -P 11035 root@connect.weste.seetacloud.com '
  # Hermes 启动时缓存了 skill 快照到 .skills_prompt_snapshot.json
  # 新 skill 需要重启 hermes 进程才生效
  pkill -f "hermes.*chat" || true
  # 客户端发起新会话时会自动重启
'
```

---

## 5. 已知坑与排错

### 坑 1：Cython 编译必须用完整包路径（**最容易踩**）

**症状**：算法 .so 编译成功，但执行时报错：
```
module 'boncml.algorithms.<algo>' has no attribute '<algo>_core'
```

**根因**：vendored/src/spss_api/<algo>/api.py 里都有：
```python
_algo = importlib.import_module('<algo>')   # 期望加载 vendored/lib 里的 Fortran .so
```
如果 Cython 编译时用 `Extension("<algo>", ["<algo>.py"])`（顶层模块名），Python 加载算法 .so 后会把 `sys.modules['<algo>']` 指向算法模块，**抢占** vendored/lib 里同名的 Fortran .so，导致 api.py 找不到 `<algo>_core` 属性。

**修复**：编译时必须用完整包路径：
```python
Extension("boncml.algorithms.<algo>", ["boncml/algorithms/<algo>.py"])
```
这样 Cython module 的 `__name__` 是 `boncml.algorithms.<algo>`，不抢占顶层命名空间。

**判断方法**：
```python
import sys, boncml.algorithms.<algo>
print(sys.modules.get("<algo>"))  # 应为 None 或指向 vendored/lib 的 .so
```

**历史算法为什么不踩坑**：老算法模块名（如 `regress`）和 vendored lib 名（`regress_fortran`）不冲突，所以顶层用 `Extension("regress", ...)` 也没问题。新算法如 `pearson`/`spearman`/`factor`/`partial`/`roc`/`distance`，算法模块名和 vendored lib 同名，**必须用包路径**。

### 坑 2：algo_specs.so 是 CLI subcommand 的真实来源

CLI `boncml --help` 显示的算法列表来自 `boncml_cli/algo_specs.so` 里编译进去的 `SPECS` dict。新增算法后必须重编这个 .so，否则 argparse 不认识新子命令（即使 `_registry` 已经能发现）。

**症状**：
```
boncml: error: argument command: invalid choice: 'pearson' (choose from ...)
```

**修复**：按 Step 5 重编 `algo_specs.so`。

### 坑 3：inspect_dataset 不算统计算法

`_registry.get_catalog()` 返回 32 个 entry，其中 1 个是 `inspect_dataset`（数据探索工具，由 propose_analysis_plan 内部调用），**31 个才是统计算法**。

SKILL.md 算法表里 `inspect_dataset` 单独列在表末，行数计 32 但统计算法数标 31。

### 坑 4：brkdwn = descriptives 别名

`brkdwn` 算法的 `tool_name` 注册为 `run_descriptives`（不是 `run_brkdwn`）。SKILL.md 算法表只能列 `run_descriptives` 一行，否则会重复计数。

### 坑 5：Python 版本必须 3.11

编译 .so 必须用 `/root/.hermes/hermes-agent/venv/bin/python`（Python 3.11.15）。如果误用系统 `/usr/bin/python3`（3.10），Cython 产物标签会变成 `cpython-310`，运行时 Hermes 加载会失败。

### 坑 6：bash_history 清空导致操作难追踪

AutoDL 实例的 `/root/.bash_history` 经常被清空（容器重启 / 打镜像清理）。重要部署命令应另存到本地脚本或本文档，不要依赖服务器 history。

### 坑 7：Hermes banner 算法数字硬编码（手工 patch）

**位置**：`/root/.hermes/hermes-agent/cli.py:2964`（启动 banner 显示行）

**症状**：新增算法后 banner 仍显示旧数字（如 `25 SPSS 兼容统计算法`），让用户误以为算法没装上。

**根因**：banner 是 hermes-agent 上游版本里**没有**的字符串，由部署时手工 patch 加进 cli.py（hermes 原版编译产物 `cli.cpython-311-*.so` 不含此 banner）。本地部署仓库 `boncml/hermes-agent/` 同时存在 `cli.py`（手工 patch 版，含 banner）和 `cli.cpython-311-*.so`（hermes 原版，无 banner）。**服务器实际跑的是 .py**。

**当前推荐 patch**：**直接去掉数字**，避免每次新增算法都要改。banner 行应为：
```python
self.console.print(f"[{text}]  {model_short}[/]  [dim {dim}]·[/]  [dim {dim}]SPSS 兼容统计算法[/]  [dim {dim}]·[/]  [dim {dim}]/help 查看命令[/]")
```

**patch 命令**（部署 hermes-agent 后必做）：
```bash
# 服务器
sed -i 's/[0-9]\+ SPSS 兼容统计算法/SPSS 兼容统计算法/' /root/.hermes/hermes-agent/cli.py
rm -f /root/.hermes/hermes-agent/__pycache__/cli.cpython-311.pyc
```

**同步到部署仓库**：
```bash
# 本地：从服务器拉 patched cli.py 到部署仓库（与服务器路径 1:1 对应）
scp -P 11035 root@connect.weste.seetacloud.com:/root/.hermes/hermes-agent/cli.py \
    boncml/hermes-agent/cli.py
```

**部署仓库现状**（截至 2026-06-17）：
- `boncml/hermes-agent/cli.py` — patched 版（banner 无数字），与服务器 md5 一致
- `boncml/hermes-agent/cli.cpython-311-*.so` — hermes 原版编译产物（无 banner），保留作 fallback
- `boncml/hermes-agent/cli.pyi` — hermes 原版类型签名

---

## 6. 验证清单

部署完成后按顺序验证：

```bash
# 1. _registry 自动发现新算法
PYTHONPATH=/root/boncml-stat-tools /root/.hermes/hermes-agent/venv/bin/python -c "
from boncml._registry import get_catalog
cat = get_catalog()
print(f'注册算法总数: {len(cat)}')
for a in ['<NEW_ALGO>', ...]:
    print(f'  {\"✓\" if a in cat else \"✗\"} {a}')
"

# 2. CLI 子命令可用
boncml --help 2>&1 | grep <NEW_ALGO>

# 3. CLI 实跑（参数按算法 spec 填）
boncml <NEW_ALGO> --data /root/data/<...>.csv [args] --output json

# 4. Hermes 端 propose_analysis_plan 能推荐新算法
/root/.local/bin/bonc chat -q "用 <NEW_ALGO> 分析 ..." --yolo
```

---

## 7. 镜像前清理（每次打镜像必做）

参考 `pre_image_cleanup.sh`，重点清理运行时状态：

```bash
# 1. 清空 API Key
sed -i 's/^GLM_API_KEY=.*/GLM_API_KEY=/' /root/.hermes/.env
sed -i 's/^GLM_BASE_URL=.*/GLM_BASE_URL=/' /root/.hermes/.env

# 2. 删 Hermes 会话、认证、状态数据（首次启动自动重建）
rm -rf /root/.hermes/hermes-agent/sessions/
rm -f /root/.hermes/hermes-agent/state.db*
rm -f /root/.hermes/hermes-agent/auth.json
rm -f /root/.hermes/.skills_prompt_snapshot.json

# 3. 清理 shell 历史
history -c && rm -f /root/.bash_history

# 4. 清理 Python 缓存
find /root/boncml-stat-tools -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null

# 5. 清理 Cython 中间产物（重要：.c 文件相当于源码暴露）
find /root/boncml-stat-tools -name "*.c" -path "*/algorithms/*" -delete 2>/dev/null

# 6. 验证
echo "=== .env ===" && cat /root/.hermes/.env
echo "=== sessions ===" && ls /root/.hermes/hermes-agent/sessions/ 2>&1
echo "=== auth ===" && ls /root/.hermes/hermes-agent/auth.json 2>&1
echo "=== 残留 .py 检查（应只有白名单） ==="
find /root/boncml-stat-tools/boncml -name "*.py" 2>/dev/null
```

**白名单 .py 文件**（不应删除）：
- `boncml/__init__.py`
- `boncml_cli/__init__.py`、`boncml_cli/main.py`
- `vendored/src/spss_api/*/__init__.py`、`vendored/src/spss_api/*/api.py`
- `boncml/algorithms/_base.py`（如保留）

---

## 8. 文件位置速查

| 角色 | 本地路径 | 服务器路径 |
|------|---------|-----------|
| 部署仓库（含 SKILL.md） | `work_space/git_clone/boncml/hermes-agent/` | — |
| boncml 源码仓库 | `work_space/git_clone/boncml-stat-tools/` | `/root/boncml-stat-tools/` |
| Hermes Agent | `/Users/penglei/.hermes/hermes-agent/` | `/root/.hermes/hermes-agent/` |
| Hermes 配置 | — | `/root/.hermes/config.yaml`、`/root/.hermes/.env` |
| Hermes 插件 | — | `/root/.hermes/plugins/boncml-statistics`（软链） |
| Hermes Skill | `boncml/hermes-agent/skills/data-science/bonc-statistics/SKILL.md` | `/root/.hermes/skills/data-science/bonc-statistics/SKILL.md` |
| 上游算法源码 | `work_space/spss-algos-transplant/` | — |

---

## 9. 连接信息（AutoDL 实例）

```
SSH:    ssh -p 11035 root@connect.weste.seetacloud.com
密码:   b0ZPaAWAzYjj（AutoDL 控制台可重置）
OS:     Ubuntu 22.04.5 LTS
glibc:  2.35
Python: 3.11.15（Hermes venv）
Cython: 3.2.5（已装在 Hermes venv）
```

> AutoDL 实例关机后可能换端口/换机器，连接信息以 AutoDL 控制台为准。
