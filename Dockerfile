# BONCML — 统计分析 Agent 镜像
# 基于 Hermes + boncml-stat-tools，所有业务逻辑均为 Nuitka/Fortran 编译的 .so
#
# 镜像包含:
#   - Hermes Agent 框架 (编译后 .so)
#   - boncml-stat-tools 插件 (26 个统计算法)
#   - bge-m3 语义检索模型
#
# 运行: bonc chat -q "你的统计问题" --yolo

# 所有 .so 编译于 cpython-311-x86_64-linux-gnu，必须匹配 Python 3.11
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HERMES_HOME=/root/.hermes
ENV PATH=/root/.local/bin:$PATH

# ── 系统依赖 ──────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        git \
        curl \
        build-essential \
        gcc \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# SSH 适配 (AutoDL 要求)
RUN mkdir -p /var/run/sshd && \
    sed -ri 's/^PermitRootLogin\s+.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    cat /etc/ssh/ssh_config | grep -v StrictHostKeyChecking > /etc/ssh/ssh_config.new && \
    echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config.new && \
    mv /etc/ssh/ssh_config.new /etc/ssh/ssh_config

# 时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo 'Asia/Shanghai' > /etc/timezone

# ── Python 核心依赖 ──────────────────────────────────
RUN pip install --no-cache-dir \
    numpy==1.24.4 \
    pandas==2.0.3 \
    scipy \
    pyyaml \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# ── Hermes 框架 ──────────────────────────────────────
WORKDIR /root

COPY hermes-agent/ /root/.hermes/hermes-agent/

# 安装 Hermes (editable，依赖从 pyproject.toml 读取)
RUN cd /root/.hermes/hermes-agent && \
    pip install --no-cache-dir -e ".[cron,mcp,cli,pty]" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# CLI 快捷入口
RUN mkdir -p /root/.local/bin && \
    echo '#!/bin/bash\nexec /usr/local/bin/hermes "$@"' > /root/.local/bin/bonc && \
    chmod +x /root/.local/bin/bonc

# ── boncml-stat-tools 插件 ───────────────────────────
COPY boncml-stat-tools/ /root/boncml-stat-tools/

# 插件注册: symlink 到 Hermes plugins 目录
RUN ln -sf /root/boncml-stat-tools /root/.hermes/hermes-agent/plugins/boncml-stat-tools && \
    ln -sf /root/boncml-stat-tools /root/.hermes/plugins 2>/dev/null || \
    mkdir -p /root/.hermes/plugins && \
    ln -sf /root/boncml-stat-tools /root/.hermes/plugins/boncml-stat-tools

# ── Embedding 模型 (bge-m3) ──────────────────────────
# 安装 torch (CPU) + FlagEmbedding
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu \
    -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir \
    FlagEmbedding \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 下载 bge-m3 模型 (~4.3G)
RUN pip install --no-cache-dir modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    python3 -c "from modelscope import snapshot_download; \
    snapshot_download('Xorbits/bge-m3', cache_dir='/root/modelscope_cache')" && \
    pip uninstall -y modelscope

# 模型 symlink
RUN mkdir -p /root/boncml-stat-tools/vendored/models && \
    ln -sf /root/modelscope_cache/Xorbits/bge-m3 /root/boncml-stat-tools/vendored/models/bge-m3

# ── 配置 ─────────────────────────────────────────────
# boncml 插件配置
RUN cat > /root/boncml-stat-tools/config.yaml << 'EOF'
python_path: ""

embedding:
  provider: local
  model_path: /root/modelscope_cache/Xorbits/bge-m3
EOF

# Hermes 配置模板 (需要用户填入 API key)
RUN mkdir -p /root/.hermes && \
    cat > /root/.hermes/config.yaml << 'EOF'
# 请将 <YOUR_API_KEY> 替换为实际的 API Key
model:
  provider: zai
  name: glm-5.1
  base_url: https://open.bigmodel.cn/api/coding/paas/v4
  api_key: <YOUR_API_KEY>
EOF

# ── JupyterLab (AutoDL 推荐) ─────────────────────────
RUN pip install --no-cache-dir \
    jupyterlab>=3.0.0 \
    ipywidgets \
    matplotlib \
    jupyterlab_language_pack_zh_CN \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# ── 清理 ─────────────────────────────────────────────
RUN rm -rf /tmp/* /root/.cache/pip

WORKDIR /root

EXPOSE 22 6006

CMD ["/usr/sbin/sshd", "-D"]
