# Unified Dataset

这个目录是 FMU orchestration pipeline 的统一数据集根目录。数据集把原始来源整理成一致的 `asset` / `case` 结构，并且以 `simple` / `complex` 作为唯一正式的 case 主分类。

## 数据集概览

- `asset`：可检索、可复用的 FMU 资源单元
- `case`：一个完整编排任务，包含需求、MBSE 结构、参考解和评测工件
- 正式 case 分类：`simple` / `complex`
- 当前快照规模：
  - `assets = 181`
  - `cases = 151`
  - `simple = 107`
  - `complex = 44`
  - 支持 execution metrics 的 case：`151`
  - 支持 numerical fidelity 的 case：`140`
  - 支持 decision accuracy 的 case：`145`

当前 case 来源分布：

- `benchmark_single_fmu_case = 137`
- `dtaas_multi_fmu_case = 9`
- `manual_multi_fmu_case = 5`

当前 asset 来源分布：

- `benchmark_single_fmu = 137`
- `dtaas_example_fmu = 30`
- `manual_case_fmu = 14`

## 整体指标快照

下面这些指标直接概括当前数据集的整体情况，默认以当前仓库里的 `indexes/*.jsonl` 和 `manifests/*.json` 为准。

### 1. 总体规模与能力覆盖

| 指标组 | 指标 | 当前值 |
| --- | --- | --- |
| 规模 | `assets` | `181` |
| 规模 | `cases` | `151` |
| 分类 | `simple / complex` | `107 / 44` |
| case 来源 | `benchmark / dtaas / manual` | `137 / 9 / 5` |
| asset 来源 | `benchmark / dtaas / manual` | `137 / 30 / 14` |
| 检索 oracle | `equivalence_class / exact_asset_set` | `137 / 14` |
| 能力覆盖 | `supports_execution_metrics` | `151` |
| 能力覆盖 | `supports_numerical_fidelity` | `140` |
| 能力覆盖 | `supports_decision_accuracy` | `145` |

### 2. 分类和来源交叉分布

| case source_type | `simple` | `complex` | total |
| --- | --- | --- | --- |
| `benchmark_single_fmu_case` | `107` | `30` | `137` |
| `dtaas_multi_fmu_case` | `0` | `9` | `9` |
| `manual_multi_fmu_case` | `0` | `5` | `5` |

`complex` 的构成进一步拆开是：

- `single_fmu_high_port = 30`
- `multi_fmu = 14`

### 3. 结构复杂度摘要

| case_category | cases | `fmu_count` | `connection_count` | `stage_count` | `ground_truth_port_count` | `monitored_output_count` |
| --- | --- | --- | --- | --- | --- | --- |
| `simple` | `107` | `1` 固定 | `0` 固定 | `0` 固定 | `1-148`，均值 `34.87` | `1-20`，均值 `2.64` |
| `complex` | `44` | `1-5`，均值 `1.68` | `0-10`，均值 `1.70` | `0-2`，均值 `0.23` | `15-321`，均值 `151.55` | `1-25`，均值 `5.00` |

这组数值有两个需要直接说明的点：

- `simple` 当前全部都是单 FMU、零连接、零 stage
- `complex` 的均值看起来不高，是因为其中有 `30` 个 case 属于“单 FMU 但端口很多”的高端口 benchmark

### 4. 结构分布

`fmu_count` 分布：

- `1 => 137`
- `2 => 4`
- `3 => 6`
- `4 => 2`
- `5 => 2`

`stage_count` 分布：

- `0 => 142`
- `1 => 8`
- `2 => 1`

非零 `connection_count` 分布：

- `2 => 2`
- `3 => 2`
- `4 => 2`
- `5 => 2`
- `7 => 3`
- `8 => 2`
- `10 => 1`

## 目录结构

```text
dataset/
├── assets/
├── cases/
├── indexes/
├── manifests/
├── schemas/
├── sources/
└── tools/
```

各目录职责如下：

- `sources/`：搬运后的原始数据源，当前主要包括 benchmark、DTaaS examples 和 manual cases
- `assets/`：规范化后的 FMU 资源，每个 asset 一个目录
- `cases/`：规范化后的任务定义，每个 case 一个目录
- `indexes/`：面向程序消费的 JSONL 索引
- `manifests/`：数据集级别汇总信息
- `schemas/`：主要 JSON 文件对应的 schema
- `tools/`：迁移、重建、校验和 library 构建脚本

## 核心概念

### Asset

`assets/<asset-id>/` 表示一个可被检索和复用的 FMU。典型目录内容：

- `asset.json`：统一后的 asset 主描述
- `metadata.json`：原始或补充元数据
- `description.md`：人类可读描述
- `model.fmu`：实际 FMU 文件

`asset.json` 里通常包含：

- `asset_id`
- `source_type`
- `name`
- `fmu_relpath`
- `metadata_relpath`
- `inputs` / `outputs` / `ports`
- `capabilities`
- `default_experiment`
- `provenance`

### Case

`cases/<case-id>/` 表示一个完整任务。一个 case 不只是问题描述，还绑定了 ground truth、参考解和评测工件。典型目录内容：

- `case.json`：任务主描述
- `solution.json`：参考编排解
- `retrieval_reference.json`：检索 oracle
- `verification_requirement.json`：验证需求
- `verification_result.json`：参考验证结论
- `trajectory_manifest.json`：轨迹文件说明
- `ground_truth_trajectory.csv`：存在时提供数值对齐基准
- `input_trajectory.csv`：存在时提供外部输入轨迹
- `notes.md`：可选的人工说明

## `simple` / `complex` 分类

### 正式分类字段

当前数据集的正式 case 主分类写在：

- `cases/<case-id>/case.json` 的 `case_category`
- `indexes/cases.jsonl` 的 `case_category`

允许值只有：

- `simple`
- `complex`

### 分类规则

当前规则 ID 为 `simple_complex_v1`，分类逻辑如下：

1. `ground_truth_asset_ids` 数量大于 1，则为 `complex`
2. 否则，如果单 FMU case 的 `ground_truth_port_count >= 150`，则为 `complex`
3. 其他情况为 `simple`

对应复杂度指标写在 `complexity_metrics` 中，当前固定包含：

- `rule_id`
- `fmu_count`
- `connection_count`
- `stage_count`
- `ground_truth_port_count`
- `ground_truth_input_count`
- `ground_truth_output_count`
- `monitored_output_count`
- `single_fmu_port_threshold_for_complex`

### 当前数据分布

当前 151 个 case 的分类结果如下：

- `simple = 107`
- `complex = 44`

其中 `complex` 由两部分组成：

- `14` 个多 FMU case
- `30` 个单 FMU 但端口数达到阈值的 benchmark case

这意味着 `complex` 不等价于“多 FMU”。例如某些 benchmark case 虽然只有一个 ground-truth asset，但如果端口很多，仍然属于 `complex`。

### 不要混用的旧概念

下面这些字段仍然可能出现，但它们不再是数据集主分类：

- `solution.json` 里的 `schedule.kind`
- 某些历史文档中的 `single_fmu` / `multi_fmu`
- 运行时或 backend 层面的 execution mode

它们描述的是参考解形态或执行形态，不等于当前 benchmark split。做数据集层面的统计、分桶或对比时，应始终以 `case_category` 为准。

## Case 文件说明

### `case.json`

`case.json` 是 case 的主入口，通常包括：

- `title` / `description`
- `requirement`
- `mbse`
- `ground_truth_asset_ids`
- `candidate_asset_ids`
- `case_category`
- `complexity_metrics`
- `solution_relpath`
- `evaluation_artifacts`
- `expected_behavior`
- `provenance`

其中几个重要字段：

- `requirement`：自然语言需求、信号关注点等
- `mbse`：组件、连接、邻接关系和 `system.sysml` 的相对路径
- `ground_truth_asset_ids`：该 case 的标准 asset 集合
- `candidate_asset_ids`：检索阶段允许选择的候选 asset 范围
- `evaluation_artifacts`：指向检索、验证和轨迹工件

### `solution.json`

`solution.json` 描述参考编排方案，常见字段包括：

- `selected_asset_ids`
- `connections`
- `external_inputs`
- `monitored_outputs`
- `schedule`
- `execution_order`
- `stages`
- `extensions`

其中：

- 单 FMU case 通常只有一个 `selected_asset_id`，`connections` 为空
- 多 FMU 或 staged case 会显式给出连接关系、执行顺序和各 stage 配置
- `extensions` 可承载 fault injection、model swap、runtime IO 和原始配置文件路径等补充信息

### 评测工件

每个 case 都会带一组标准评测工件：

- `retrieval_reference.json`
  - benchmark case 主要使用 `equivalence_class`
  - manual / DTaaS multi-FMU case 主要使用 `exact_asset_set`
- `verification_requirement.json`
  - 定义需求文本、关注信号、时间窗口、判定规则和容差
- `verification_result.json`
  - 给出参考结论、证据基础和是否支持 decision accuracy
- `trajectory_manifest.json`
  - 说明 ground truth/input 轨迹文件、时间列、信号列、别名和 stage segment

能力覆盖上：

- 全部 `151` 个 case 支持 execution metrics
- `137` 个 benchmark case 支持 numerical fidelity
- 同样有 `137` 个 benchmark case 支持 decision accuracy

## 数据集级索引与清单

### `indexes/`

- `assets.jsonl`
  - 轻量资产索引
  - 当前字段包括 `asset_id`、`name`、`source_type`、`relative_dir`
- `cases.jsonl`
  - 轻量 case 索引
  - 当前字段包括 `case_id`、`case_category`、`complexity_metrics`、`source_type`、`ground_truth_asset_ids`、`retrieval_oracle_mode` 和能力开关

推荐把 `indexes/*.jsonl` 作为脚本批量消费入口，而不是递归扫描所有 case 目录。

### `manifests/`

- `dataset_manifest.json`
  - 数据集总规模与分类统计
  - 当前记录 `asset_count = 181`、`case_count = 151` 和 `case_category_counts`
- `benchmark_manifest.json`
  - benchmark 子集规模摘要
  - 当前记录 `assets = 137`、`cases = 137`

## Schema

主要 schema 位于 `schemas/`：

- `asset.schema.json`
- `case.schema.json`
- `solution.schema.json`
- `library_manifest.schema.json`

其中 `case.schema.json` 已经把 `case_category` 限定为 `simple | complex`。

## 重建与校验

完整重建命令：

```bash
python3 -m dataset.tools.rebuild_dataset \
  --dataset-root dataset \
  --library-root pipeline/resources/fmu_library
```

这个过程会：

1. 清空并重建 `assets/`、`cases/`、`indexes/`、`manifests/`
2. 迁移 benchmark、manual cases 和 DTaaS examples
3. 执行数据集校验
4. 重建 pipeline FMU library

只做校验时可运行：

```bash
python3 -m dataset.tools.validate_dataset \
  --dataset-root dataset \
  --library-root pipeline/resources/fmu_library
```

校验会刷新索引和 manifest，并检查：

- 关键 JSON 文件是否存在
- 必填字段是否完整
- `solution.json` 和评测工件是否齐全
- 重新计算并写回 `case_category` 与 `complexity_metrics`
- `provenance.source_root` 是否能在 `sources/` 下找到

## 使用约定

- 需要按难度分桶时，只使用 `case_category`
- 需要看结构复杂度时，读取 `complexity_metrics`
- 需要看参考编排方案时，读取 `solution.json`
- 需要批量统计时，优先读取 `indexes/cases.jsonl`
- 需要确认整体规模时，读取 `manifests/dataset_manifest.json`

如果后续再调整分类阈值或引入新的 case taxonomy，应同步更新：

- `dataset/tools/validate_dataset.py`
- `cases/*/case.json`
- `indexes/cases.jsonl`
- `manifests/dataset_manifest.json`
- 本 README
