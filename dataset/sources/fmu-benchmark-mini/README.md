# FMU Benchmark Mini

## 1. 项目简介（What is this）

`fmu-benchmark-mini/` 是一个面向快速迭代的 FMU 子集数据集。
它从完整数据集 `fmu-benchmark/` 中筛选出 **FMI 2.0**、**linux64** 且 **可执行** 的 FMU，并保留统一的目录结构与索引文件。
在此基础上，本子集还为每个 FMU 生成了“语义增强”产物（能力画像、行为特征等），并可作为 SysML 反向构建的输入。

## 2. 数据集来源与构建流程（Where it comes from）

本数据集由一条可复现的流水线生成。
下面按“输入 → 脚本 → 输出”的顺序，详细描述从上游仓库到 `fmu-benchmark-mini/` 的全过程。
文中命令默认在仓库根目录执行。

运行第 2.3/2.5/2.6 步时需要安装相应 Python 依赖：

- `benchmark_fmus.py`：`fmpy`, `numpy`
- `enhance_fmu_semantics.py`：`fmpy`, `numpy`, `pandas`（可选：`scipy`, `tqdm`, `requests`）

### 2.1 获取原始 FMU（上游仓库 → `originalFMU/`）

开发者从多个 GitHub 仓库克隆原始 FMU（仓库名建议保持不变，便于脚本识别），放置到仓库根目录的 `originalFMU/` 下。
上游来源列表见 `fmu-benchmark/README.md` 的 `Sources` 小节，典型包括：

- `fmi-cross-check`
- `Reference-FMUs`
- `altairengineering/fmus`
- `FMI30TestFMUs`
- `FMUSDK`
- `example-fmus`
- `Test-FMUs`
- `dymola-fmi-compatibility`

### 2.2 FMU 预处理与标准化（`build_benchmark.py` → `fmu-benchmark/`）

脚本：`fmu-benchmark/scripts/build_benchmark.py`

作用：

- 扫描 `originalFMU/` 中不同来源的 FMU，并重排为统一目录结构。
- 从 FMU 内部的 `modelDescription.xml` 抽取结构化元数据，生成 `*.metadata.json`。
- 生成全局索引 `index.csv` 与工具映射 `tools.csv`，并尽可能生成单 FMU 的 SSP 描述（`.ssd/.ssv`）。

示例（在仓库根目录执行）：

```bash
python3 fmu-benchmark/scripts/build_benchmark.py --source originalFMU --output fmu-benchmark -v
```

### 2.3 能力探测（`benchmark_fmus.py` → 可执行性 + `*.timeseries.csv`）

脚本：`fmu-benchmark/scripts/benchmark_fmus.py`

作用：

- 对 `fmu-benchmark/fmus/` 下的 FMU 做轻量仿真探测（验证可加载/可运行）。
- 成功：在 FMU 同目录生成 `*.timeseries.csv`（输入/输出时序）。
- 失败：在 FMU 同目录生成 `*.fail.flag`（用于后续筛除）。
- 同时输出一个汇总 CSV 报告（可放到 `fmu-benchmark/results/`）。

示例：

```bash
python3 fmu-benchmark/scripts/benchmark_fmus.py fmu-benchmark/fmus \
  --parallel --workers 4 \
  -o fmu-benchmark/results/benchmark_report.csv
```

### 2.4 构建 mini 子集（`filter.py` → `fmu-benchmark-mini/`）

脚本：`fmu-benchmark/scripts/filter.py`

默认筛选逻辑（对应 `fmu-benchmark-mini/` 的“可执行 FMI2.0 linux64 子集”定位）：

- `fmiVersion == 2.0`
- `platform == linux64`
- FMU 目录内不存在 `*.fail.flag`
- 存在且“有动态”的 `*.timeseries.csv`（默认开启，可用 `--no-require-timeseries` 关闭）
- `*.metadata.json` 满足基本描述质量（`--min-desc-ratio` 可调）

示例：

```bash
python3 fmu-benchmark/scripts/filter.py --input fmu-benchmark --output fmu-benchmark-mini
```

### 2.5 FMU 语义增强（`enhance_fmu_semantics.py` → `*.semantic.json` 等）

脚本：`fmu-benchmark-mini/scripts/enhance_fmu_semantics.py`

作用：

- 解析元数据（来自 `*.metadata.json` 与 FMU 内部 `modelDescription.xml`）。
- 执行可复现的行为探测场景（`step` / `ramp` / `sine`）并提取行为特征。
- 在 **FMU 同目录** 落盘语义产物（不修改 `.fmu` 本体）。

示例：

```bash
python3 fmu-benchmark-mini/scripts/enhance_fmu_semantics.py \
  --root fmu-benchmark-mini/fmus --jobs 8 --resume --progress
```

### 2.6 SysML 反向构建（`sysml_reverse_build/pipeline.py` → `*.sysml`）

核心实现：`sysml_reverse_build/pipeline.py`
批处理入口：`reverse_build_sysml.py`

作用：

- 输入：每个 FMU 目录内的 `*.semantic.json`。
- 输出：同目录生成 `*.sysml` 与 `*.sysml.build_log.json`（最多 5 轮“生成/修复 → 语法校验”闭环）。
- 批处理时会生成汇总报告（例如某些 `tool_version` 目录下的 `sysml_reverse_build_report.md/json`）。

示例（LLM API 模式）：

```bash
export LLM_API_KEY=...
python3 reverse_build_sysml.py --root-dir fmu-benchmark-mini/fmus --jobs 4 --llm-concurrency 2
```

示例（离线模板 smoke）：

```bash
python3 reverse_build_sysml.py --root-dir fmu-benchmark-mini/fmus --llm-mode template
```

## 3. 数据集内容结构（What’s inside）

整体布局：

```text
fmu-benchmark-mini/
├── README.md
├── index.csv
├── tools.csv
├── schemas/
│   └── fmu_metadata.schema.json
├── fmus/
│   └── 2.0/
│       └── <me|cs>/linux64/<tool_id>/<tool_version>/<model>/
│           ├── <model>.fmu
│           ├── <model>.metadata.json
│           ├── <model>.timeseries.csv          # 来自 benchmark_fmus.py
│           ├── <model>.timeseries.csv.gz       # 来自 enhance_fmu_semantics.py
│           ├── <model>.semantic.json           # 来自 enhance_fmu_semantics.py
│           ├── <model>.report.md               # 来自 enhance_fmu_semantics.py
│           ├── <model>.errors.json             # 可选：语义增强失败时
│           ├── <model>.sysml                   # 下游：SysML 反向构建
│           └── <model>.sysml.build_log.json    # 下游：构建日志
├── ssp/
│   └── single-fmu/2.0/<me|cs>/linux64/<tool_id>/<tool_version>/
│       ├── <model>.ssd
│       └── <model>.ssv
└── scripts/
    └── enhance_fmu_semantics.py
```

关键文件说明：

- `index.csv`：本子集的全局索引（每行一个 FMU），包含 `dataset_id`、`tool_id`、`tool_version`、`path_to_fmu`、`path_to_metadata` 等字段（路径为相对路径）。
- `tools.csv`：本子集涉及的工具 ID 映射。
- `schemas/fmu_metadata.schema.json`：`*.metadata.json` 的校验 schema。
- `*_ref.csv` / `*_in.csv` / `*_simopt.json`：部分 FMU 的参考输出/输入或仿真选项文件（可选，通常由上游或预处理阶段提供，并在 `*.metadata.json` 中被引用）。

## 4. FMU 语义增强说明（Enhanced semantics）

语义增强面向“能力画像”而非精确系统辨识。
核心输出文件为 `*.semantic.json`，通常包含：

- `metadata_summary`：模型与 FMU 基本信息摘要。
- `variables`：输入/输出/参数/内部变量清单与筛选结果。
- `probe_config`：`step/ramp/sine` 探测场景与仿真参数（时长、步长、超时、随机种子等）。
- `features` 与 `fmu_profile`：变量级与 FMU 级行为特征、标签与摘要信息。
- `log_summary`：运行信息与错误摘要（若三场景全部失败，另有 `*.errors.json`）。

注意：

- 语义增强不会修改 `.fmu`，产物与 FMU 同目录共存。
- 即使使用固定 `--seed`，不同 FMI runtime/数值设置仍可能导致细微差异；建议同时记录依赖版本与关键参数。

## 5. 与 SysML 反向构建的关系（Downstream usage）

SysML 反向构建以 `*.semantic.json` 为输入，而不是直接解压/解析 `.fmu`。
生成物与语义文件同目录：

- `*.sysml`：生成的 SysML 模型文本。
- `*.sysml.build_log.json`：构建日志（包含校验错误、修复轮次等，最多 5 轮）。

如果你只关心“能跑通流程”，可先用 `--llm-mode template` 做离线 smoke，再切换到 API 模式获得更完整的 SysML。

## 6. 可复现性与版本说明（Reproducibility & versioning）

推荐的可复现实践：

- 选择规则可追溯：mini 子集由 `filter.py` 的筛选规则 + `benchmark_fmus.py` 的 `*.fail.flag`/`*.timeseries.csv` 决定。
- 派生文件自带版本：`*.semantic.json` 与 `*.sysml.build_log.json` 均包含 `version` 与 `timestamp` 字段。
- 完整性校验：可运行 `python3 fmu-benchmark/scripts/validate_dataset.py fmu-benchmark-mini` 检查索引与文件结构一致性。
- 许可证：FMU 的许可证保持上游仓库原样；完整构建流程会在 `fmu-benchmark/LICENSES/` 收集常见 license 文件，或直接查看 `originalFMU/` 对应仓库。
