# BONCML Workspace 多 Agent 协作平台

让多个 AI 智能体（Agent）在统一的工作空间中协同完成复杂任务。平台以 **Spec 驱动的工作流** 为核心，支持从需求澄清、方案设计、任务执行到评审交付的全流程自动化编排——它把统计分析、方案撰写、评审等任务组织成 Spec → Issue → DAG → Artifacts 的流水线，让多个 Agent 在统一工作空间中并行完成端到端任务。

## 核心功能模块

### 2.1 Workspace 与 Rooms 工作区管理

- **Workspace**：顶层工作空间，承载所有协作活动
- **Rooms（房间）**：工作空间下可创建多个房间（如 #2、#3、#no1、#no2、#no3），每个房间是一个独立的协作上下文
- 房间内包含 **MEMBERS**（人类成员）和 **AGENTS**（智能体成员）

### 2.2 Channel 频道创建与管理

- 支持创建 **Public（公开）** 和 **Private（私有）** 两种频道
- 创建时可设置名称、描述、可见性
- 可从 Agent 列表中选择成员加入频道（如 algo、需求、方案、评审）
  ![image.png](https://codewithgpu-image-1310972338.cos.ap-beijing.myqcloud.com/748899-240646441-aNajrg9gMwKBuWIMtOJN.png)

### 2.3 多 Agent 协作系统

平台内置多种角色化智能体，各司其职：

| Agent | 职责 |
|-------|------|
| 需求 | 负责需求澄清，产出 Spec 并向用户提出待确认项 |
| 方案 | 将需求整理成 spec、issue 拆解、assignment plan，最终交付 Markdown 文档 |
| 评审 | 检查边界、风险与验收标准，提出修改意见 |
| algo | 算法相关任务的执行 Agent |

每个 Agent 具有独立的配置面板：

- 运行时绑定（Runtime）
- 底层模型选择（如 gpt-5-mini）
- 可见性（Workspace 级别）
- 并发数设置
- 指令（Instructions）、Skill、环境变量、自定义参数

### 2.4 对话式交互（CHAT 视图）

- 支持在房间内通过自然语言与 Agent 对话
- 使用 `/spec` 命令发起 Spec 定义任务
- 支持 `@Agent 名` 提及特定 Agent 并派发任务
- Agent 会自动回复进展汇报、待办/阻塞项、下一步建议
- 用户可通过简短回复快速决策（如"1.研发；2.docker；3.只要一份 Markdown 文档即可"）
  ![image.png](https://codewithgpu-image-1310972338.cos.ap-beijing.myqcloud.com/748899-299742479-k5U4P5a9G39SIHKQq0Kp.png)
  ![image.png](https://codewithgpu-image-1310972338.cos.ap-beijing.myqcloud.com/748899-492778800-mh4ybgu6DCKnyBTmzdMT.png)

### 2.5 Spec 驱动的任务编排

完整的 Spec 生命周期：

1. **Clarifying（澄清）** → 需求 Agent 产出 SPEC 文档，列出 Confirmed Scope 和 Open Questions
2. **Drafting（起草）** → 生成 Spec Draft（v1）
3. **Issue Plan（拆解）** → 将 Spec 拆解为多个 Issue
4. **Assignment Plan（分配）** → 将 Issue 分配给对应 Agent
5. **Execution（执行）** → 各 Agent 并行工作
6. **Review（评审）** → 评审 Agent 审核
7. **Completed（完成）** → 最终交付

### 2.6 DAG 任务可视化（TASKS 视图）

- 以有向无环图（DAG）形式展示所有 Issue 及其依赖关系
- 每个节点显示 Issue 标题、负责 Agent、当前状态（待办/完成）
- 支持缩放和平移操作
- 点击节点可查看 Issue 详情

示例任务链路：

```
收集与确认输入资料 → 为每个 Agent 编写故障模型与排查步骤
                   → 编写端到端调用链与 ASCII 流程图
                   → 准备示例故障场景与日志片段
                        ↓
              编写诊断命令清单与快速决策树（Checklist）
                        ↓
                 撰写完整 Markdown 文档草稿
                        ↓
                  内部评审与修改（@评审）
                        ↓
                 发布与归档（Ready for use）
```

![image.png](https://codewithgpu-image-1310972338.cos.ap-beijing.myqcloud.com/748899-92719230-WT7l3oD2kbw1oefeeG89.png)

### 2.7 Artifacts 产物管理

- 每个 Spec 下关联一组版本化产物
- 产物类型包括：
  - 澄清记录（Clarifications）：v1、v2、v3 等多版本
  - Spec Draft：正式需求文档
  - Issue Plan：拆解计划
  - Assignment Plan：分配计划
  - Approval：批准记录
  - 代码/文档产物：如 `agent_v1_inputs.md`、`orchestrator_call_flow.txt`、`agent-troubleshooting.md`
  - 交付物清单：最终交付汇总
- 支持预览和下载
  ![image.png](https://codewithgpu-image-1310972338.cos.ap-beijing.myqcloud.com/748899-363294044-jel2l7xCONyKyXxlryEQ.png)

### 2.8 多阶段工作流 Pipeline

房间顶部展示完整的工作流阶段进度条：

```
DATA QUALITY → ANALYSIS PLAN → BONCML RUN → EXEC SUMMARY → COMMAND DECK
```

每个阶段对应任务执行的不同环节，可视化追踪整体进展。

### 2.9 Runtime 运行时管理

平台支持接入多种 CLI Runtime 作为 Agent 的执行引擎：
![image.png](https://codewithgpu-image-1310972338.cos.ap-beijing.myqcloud.com/748899-671089557-KCvou19Yl4tpPO9ZFXnD.png)

| Runtime | 说明 |
|---------|------|
| Copilot | GitHub Copilot CLI 1.0.59 |
| Kiro | Kiro CLI |
| Claude | Anthropic Claude |
| Opencode | 开源代码 Agent |
| Openclaw | 开源 Agent 运行时 |
| Hermes | Hermes Agent 运行时 |

运行时管理功能：

- 查看在线状态、健康度
- 支持"我的"和"全部"筛选视图
- 状态过滤（在线 / 最近失联 / 离线 / 即将清理）
- 支持连接远程机器扩展算力
- CLI 版本追踪（如 v0.4.0-20-gb405b0c3）

### 2.10 运行时监控与费用统计

每个 Runtime 的详情页提供：

- **费用统计**：30 天费用（如 $1.61）、缓存节省额
- **Token 用量**：输入/输出 Token 统计（如 804.5K）
- **时序图表**：按天 / 按小时 / 热力图 / 费用 / Token 多维展示
- **按智能体分摊**：展示各 Agent 消耗的 Token 和费用占比
- **服务中的 Agent**：实时显示各 Agent 在线状态和处理进度

### 2.11 Issue 管理系统

每个 Issue 具备完整的项目管理属性：

- 状态流转：待办 → 审核中 → 完成
- 完成标准（DoD）：明确的验收条件列表
- Delivery Requirement：通过 `upload_artifact` 工具提交交付物
- 父子 Issue 关联：支持 Issue 层级结构
- 执行日志：记录 Agent 处理过程（首次运行、处理中）
- Pull Request 关联：支持通过 PR 分支名或正文引用自动关联
- 动态流（Activity）：实时展示 Agent 执行状态、工具调用次数、耗时
  ![image.png](https://codewithgpu-image-1310972338.cos.ap-beijing.myqcloud.com/748899-753966042-KHYaX7nZVbFY7YzickXM.png)

### 2.12 Agent 智能体详情与性能统计

Agent 详情页展示：

- 近 30 天表现：总执行次数（如 167 次）、成功率（99%）、平均耗时（55s）
- 最近工作列表：展示任务名称、耗时、状态
- 当前进行中任务：实时追踪
- 配置面板：动态 / Task / 指令 / Skill / 环境变量 / 自定义参数
  ![image.png](https://codewithgpu-image-1310972338.cos.ap-beijing.myqcloud.com/748899-737432754-ocbOGSQvKiZJDQP1uMCk.png)

### 2.13 最终文档交付

平台产出的最终交付物为结构化 Markdown 文档，示例：

- 《BONCML Agent 4-agent 链路调试指南（v1.0）》
- 包含：调用链 ASCII 序列图、全链路可观测性、典型故障分类与逐步排查、容器级诊断命令、快速决策树、最佳实践与预防

## 典型使用流程

1. 创建 Room → 添加 Agent 成员
2. 在 CHAT 中用 `/spec` 命令描述需求
3. 需求 Agent 自动澄清，产出 SPEC
4. 用户确认后进入 Drafting 阶段
5. 系统自动拆解 Issue → 生成 Assignment Plan
6. 各 Agent 按 DAG 依赖关系并行执行
7. 方案 Agent 产出中间产物并请求审核
8. 评审 Agent 审核后进入最终交付
9. 产出 Markdown 文档 → 通过 Artifacts 下载使用

## 技术亮点

- **Spec-Driven Orchestration**：以 Spec 为协作核心，避免 Agent 之间的混乱沟通
- **DAG 任务编排**：自动计算依赖关系，支持并行执行提升效率
- **多 Runtime 支持**：可对接 GitHub Copilot、Claude、自定义 Agent 等多种执行引擎
- **成本可观测**：实时追踪每个 Agent、每个 Runtime 的 Token 消耗与费用
- **人机协同**：用户可随时通过对话介入决策，Agent 主动汇报进展与阻塞
- **版本化产物管理**：所有中间产物和最终交付物可追溯、可下载
- **可扩展架构**：支持连接远程机器、灵活配置 Agent Skill 与环境变量
