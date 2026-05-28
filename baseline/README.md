# Baseline 方法说明

本目录实现了一组面向评测器的 baseline 与消融实验方法。整体实现采用统一的三阶段装配方式：

- Stage 1：需求分解（Requirement Decomposition）
- Stage 2：仿真单元匹配（Simulation Units Matching）
- Stage 3：仿真程序构建（Simulation Program Construction）

每一种方法都通过 `bundles/` 下的注册文件组装为一个 `MethodBundle`，再由 `common/bundle_factory.py` 注入固定的 `method_name` 与独立 `workspace_root`。因此，这里的 baseline 不是松散的概念说明，而是由具体阶段实现模块直接拼装出的可评测方法。

## Baselines

### B1: Rule-Based Sequential Pipeline

这是一个完全确定性的 baseline，由以下三个模块直接构成：

- Stage 1：`stage1/rule_template.py`
- Stage 2：`stage2/graph_match_only.py`
- Stage 3：`stage3/static_rule_scheduler.py`

具体构建方式如下：

- 需求分解阶段使用规则模板解析器，从需求文本中抽取目标、验收指标、运行区间以及候选组件信息；随后复用现有 grounding 与打分流程，将规则生成的原始 task set 映射到 MBSE 上下文，并只保留单个最佳候选。
- 仿真单元匹配阶段不依赖语义检索分数，而是先建立严格的结构可行性约束。实现中会根据信号支持、组件角色兼容性、拓扑谓词、FMI 接口可行性等条件构造 structural cost matrix；再按任务逐个贪心选择可行 FMU，并实例化端口级编排图。
- 仿真程序构建阶段采用静态规则调度。实现会读取匹配后的编排图，识别链式、星型、顺序型、环路监控型等图结构，再基于固定规则生成节点顺序、通信网格、每节点调度表与连接记录；不做自适应优化，只输出确定性的执行计划。

实现特点：

- 无 LLM 依赖的核心决策链路。
- 所有关键选择均由手工规则、固定优先级和确定性排序完成。
- 适合作为最稳健、最可解释的顺序执行基线。

### B2: LLM + Local Retrieval + Rule Orchestration

这是一个“LLM 负责理解、规则负责落地”的混合 baseline，由以下模块构成：

- Stage 1：`stage1/top1_llm.py`
- Stage 2：`stage2/semantic_retrieval_only.py`
- Stage 3：`stage3/static_rule_scheduler.py`

具体构建方式如下：

- 需求分解阶段调用现有 LLM 风格分解逻辑，但强制只保留一个候选 task set，即 top-1 decomposition。若 LLM 原始候选为空，则退化为一个最小的 fallback task set。之后同样复用 grounding、修复、校验与 verifiability scoring 流程，确保输出仍符合评测器接口。
- 仿真单元匹配阶段采用本地语义检索构造 semantic cost matrix，并叠加 source type、runtime capability、grounded component、grounded component type 等先验偏置；随后按任务逐行选择语义代价最低的 FMU，再调用端口图实例化逻辑检查闭包是否成立。
- 仿真程序构建阶段继续使用静态规则调度器，因此脚本执行结构仍然是确定性的。也就是说，B2 的不确定性主要来自需求理解，后续 orchestration 保持规则化。

实现特点：

- 将 LLM 的作用限制在需求理解与任务拆解，不把生成式能力扩散到调度层。
- 单元匹配依赖本地语义代价矩阵，而非图全局优化。
- 最终程序构造仍然沿用固定模板和规则执行启发式。

### B3: Heuristic Graph-Aware Pipeline

这是一个更强调拓扑感知的 baseline，由以下模块构成：

- Stage 1：`stage1/heuristic_neighborhood.py`
- Stage 2：`stage2/greedy_hybrid.py`
- Stage 3：`stage3/greedy_multirate_scheduler.py`

具体构建方式如下：

- 需求分解阶段首先对需求文本、组件名称、组件类型、端口名和验收指标做 token 级匹配，给每个 MBSE 组件计算 anchor score；再从高分锚点出发，沿邻接关系扩展局部 neighborhood，形成面向拓扑局部的 task set。每个 task 会显式记录 seed component、扩展来源与 anchor trace。
- 仿真单元匹配阶段同时计算 semantic cost 与 structural cost，并按固定权重组合为 combined cost。初次分配采用局部贪心；如果端口图闭包失败，则使用一次基于冲突对的 repair，排除冲突任务-FMU 对后重新贪心匹配。这个版本保留结构约束，但移除了全局最优求解。
- 仿真程序构建阶段使用启发式多速率调度器。实现会读取 FMU 的默认步长或内部固定步长，先生成 base tick，再按图依赖顺序与边约束贪心调整节点周期，随后生成 communication grid、per-node schedule、ZOH 保持策略和最终 execution plan。

实现特点：

- 从需求分解开始就引入 MBSE 邻域与拓扑局部信息。
- 匹配阶段是语义与结构的混合贪心，而不是纯检索或纯图匹配。
- 调度阶段显式处理多速率兼容问题，是三条 baseline 中最接近图驱动协同仿真的实现。

## Ablation Studies

本目录中的消融实验按“三阶段替换”的方式实现。每个消融 bundle 只替换一个阶段，其他阶段通过 `common/current_stages.py` 包装当前主线实现，从而保证比较对象聚焦在单一模块差异。对于 Stage-1 ablation，当前 Stage 2 仍被复用，但会关闭 benchmark single-FMU fallback 和 MBSE component-cover fallback，避免下游恢复路径覆盖掉被测的分解结果。

### Requirement Decomposition

#### Top-1 LLM Decomposition

对应实现：

- Bundle：`bundles/ablation_stage1_top1_llm.py`
- Stage 1：`stage1/top1_llm.py`
- Stage 2 / 3：`common/current_stages.py`

实现方式：

- 使用 `_generate_raw_tasksets_via_llm(..., max_candidates=1)` 强制只生成一个分解候选。
- 沿用现有 grounding、invalid grounding repair 与 verifiability score 计算逻辑。
- 去除 conformal set 相关元数据，只输出单个 evaluator-compatible task set。

这对应“将集合式、校准式分解退化为单个 LLM 分解结果”的消融。

#### Rule Template Decomposition

对应实现：

- Bundle：`bundles/ablation_stage1_rule_template.py`
- Stage 1：`stage1/rule_template.py`
- Stage 2 / 3：`common/current_stages.py`

实现方式：

- 使用 `_generate_raw_tasksets_via_rules(...)` 从预定义规则模板生成多个原始候选。
- 对候选逐个执行 grounding 与打分，再按规则来源优先级、得分和任务数选择单个最佳模板候选。
- 当规则无法覆盖需求时，构造一个基于组件提及与端口回退的 fallback task set。

这对应“用规则模板解析器替换学习式分解模块”的消融。

#### Heuristic Neighborhood Decomposition

对应实现：

- Bundle：`bundles/ablation_stage1_heuristic_neighborhood.py`
- Stage 1：`stage1/heuristic_neighborhood.py`
- Stage 2 / 3：`common/current_stages.py`

实现方式：

- 先根据需求文本与 MBSE 组件/端口 token 重合度计算锚点分数。
- 再从锚点组件向局部邻域扩展，构造覆盖邻域行为的任务集合。
- 输出中保留 `seed_components`、`expanded_components` 与 `anchor_trace`，便于分析局部启发式如何影响后续匹配。

这对应“用拓扑局部扩展替换显式任务分解器”的消融。

### Simulation Units Matching

#### Semantic Retrieval Only

对应实现：

- Bundle：`bundles/ablation_stage2_semantic_retrieval_only.py`
- Stage 1 / 3：`common/current_stages.py`
- Stage 2：`stage2/semantic_retrieval_only.py`

实现方式：

- 仅构建 semantic cost matrix，并叠加若干 grounded prior。
- 对每个任务独立选择最低语义代价 FMU。
- 最后只把结构图实例化与闭包检查作为验证步骤，不把图结构推理用于搜索决策本身。

这对应“只有语义检索，没有结构图推理”的消融。

#### Graph Match Only

对应实现：

- Bundle：`bundles/ablation_stage2_graph_match_only.py`
- Stage 1 / 3：`common/current_stages.py`
- Stage 2：`stage2/graph_match_only.py`

实现方式：

- 先基于硬约束解释矩阵筛除不可行 FMU。
- 再按信号重合、组件别名命中、类型兼容、拓扑与接口可行性构造 structural score / cost。
- 逐任务贪心选择纯结构上最优的 FMU，不引入语义检索代价。

这对应“只有结构兼容与图模式对齐，没有语义排序”的消融。

#### Greedy Hybrid Match

对应实现：

- Bundle：`bundles/ablation_stage2_greedy_hybrid.py`
- Stage 1 / 3：`common/current_stages.py`
- Stage 2：`stage2/greedy_hybrid.py`

实现方式：

- 同时计算 semantic cost 与 structural cost，并以固定权重线性组合。
- 使用局部贪心生成首轮 assignment。
- 若图闭包失败，只执行一次基于冲突对排除的 repair，而不做全局优化或多轮联合搜索。

这对应“混合语义与结构，但去除全局优化机制”的消融。

### Simulation Program Construction

#### Static Rule Scheduler

对应实现：

- Bundle：`bundles/ablation_stage3_static_rule_scheduler.py`
- Stage 1 / 2：`common/current_stages.py`
- Stage 3：`stage3/static_rule_scheduler.py`

实现方式：

- 只接受严格 chain 或退化 single-FMU 拓扑；遇到分支、汇聚或环路直接拒绝。
- 只保留链上相邻节点的一条连接，使用固定规则生成节点顺序、连接记录、通信时间网格和逐节点执行表。
- 使用全局最粗步长作为统一通信步长，不做通信步长贪心调整，不做脚本自由生成。

这对应“完全固定模板和规则的静态调度”消融。

#### Greedy Multi-Rate Scheduler

对应实现：

- Bundle：`bundles/ablation_stage3_greedy_multirate.py`
- Stage 1 / 2：`common/current_stages.py`
- Stage 3：`stage3/greedy_multirate_scheduler.py`

实现方式：

- 先按图顺序把连接图线性化，只保留一条弱路径上的前向连接，去掉额外分支与回边。
- 再从 FMU 元数据读取默认步长中的最粗步长作为 base tick，并只生成两档周期：`base_tick` 或 `2 * base_tick`。
- 最终生成粗粒度多速率 communication grid、per-node schedule 与 ZOH 标注，但不再做精细多速率对齐。

这对应“启发式多速率构造，但不依赖学习式脚本生成”的消融。

#### LLM-Generated Orch. Script

对应实现：

- Bundle：`bundles/ablation_stage3_llm_generated_script.py`
- Stage 1 / 2：`common/current_stages.py`
- Stage 3：`stage3/llm_generated_script.py`

实现方式：

- 只把 Stage 2 的已选 FMU、端口目录与 scenario window 提供给 LLM，要求其直接生成 `UNIFIED_SOLUTION_V1` 风格的 orchestration JSON 字段，而不是复用当前主线 `compose(...)` 的结构化 middleware / adapter / loop-wrapper 路径。
- Stage 3 不允许修改 Stage 2 选中的 asset set；LLM 只能在固定 asset 集合上生成连接、顺序和调度。
- 若 LLM 输出违反 schema 或端口约束，则整包回退到一个更弱的 fixed-step fallback：保留 asset set，但清空连接并使用统一粗步长调度。
- evaluator 会把这个 bundle 生成的 `final_solution_payload` 作为 `predicted_solution.json` 中 stage3 字段的权威来源，并禁用 source/reference 对这些 stage3 字段的回填。

这对应“LLM 直接生成最终 orchestration JSON，同时保留规则式 fallback”的消融。

## 目录对应关系

- `bundles/`：定义每个 baseline / ablation 如何由三阶段模块拼装而成。
- `stage1/`：需求分解相关实现。
- `stage2/`：仿真单元匹配相关实现。
- `stage3/`：仿真程序构建相关实现。
- `common/`：bundle 构造、当前主线阶段包装、workspace 注入等公共逻辑。
- `workspaces/`：各方法独立工作区，用于隔离缓存、提示词、调试记录和中间产物。

## 设计原则

- 所有 baseline 与消融都遵守同一评测接口，只替换明确的阶段实现。
- baseline 之间不是参数切换，而是由不同的 Python 模块直接组成。
- 消融实验通过“单阶段替换，其余阶段保持 current implementation”来保证比较可解释性。
