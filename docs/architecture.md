# 项目结构

[项目首页](../README.md) · [快速开始](quickstart.md) · [数据说明](data.md) · [结果解读](results.md)

## 数据流

```mermaid
flowchart LR
    A[县域网页档案] --> C[标准化报价面板]
    B[全国价格记录] --> D[报价更新与恒定段筛查]
    C --> D
    C --> E[历史基准与县域样本比较]
    D --> E
    E --> F[逐日预警回放]
    E --> G[结果表与图件]
    F --> G
```

项目通过一个命令入口串联输入校验、统计计算、图件生成与材料导出。核心统计程序同时保存明细输出，便于定位任一汇总数值。

## 目录职责

```text
agri-price-monitor/
├── scripts/                 项目入口
├── code/                    计算、核查、绘图与导出
├── inputs/                  原始与标准化输入
│   ├── normalized_prices.csv
│   ├── reference_experiments/
│   ├── full_archive/
│   └── accepted_counts/
├── results/                 现成计算结果
│   ├── primary_15_L6.json
│   ├── precision/
│   └── alerts/
├── figures/                 独立图件
├── docs/                    项目文档
├── reports/                 分析报告和补充资料
├── environment/             固定依赖与运行环境
├── Makefile                 常用操作
└── MANIFEST_SHA256.json      完整包文件清单
```

## 主要程序

| 程序 | 职责 |
| --- | --- |
| `scripts/project.py` | 项目概况、校验、数据准备、重建与导出的统一入口 |
| `code/reproduce_all.py` | 完整计算顺序与结果比较 |
| `code/replay_frozen_science.mjs` | 主配置与组合筛查比较 |
| `code/precision_extension.mjs` | 六项增加抽样次数的精度检查 |
| `code/alerts.mjs` | 逐日预警与连续事件汇总 |
| `code/mc_precision.py` | 蒙特卡洛概率估计的精度与区间 |
| `code/verify_episode_point_statistics.py` | 低于基准持续段的更新统计 |
| `inputs/full_archive/code/reproduce.cjs` | 原始网页解析、品种覆盖与筛查 |
| `code/plot_figures.py` | 两张主图和两张补充图 |
| `code/build_docx.py` / `code/build_supplement.py` | 可编辑分析材料 |
| `code/export_native.py` | PDF 与逐页图像导出 |

## 输入、结果与生成文件

- `inputs/` 保存计算所需报价、源记录与参照资料。
- `results/` 保存交付时的主比较和明细结果；重建流程以这些内容作为核对对象。
- `reproduction/` 由运行过程生成，保存步骤日志与汇总。
- `native/` 由文档构建与导出生成，保存重新构建的 Word、PDF 和页面图像。

统计核心使用 Node.js，统计核查与图件构建使用 Python。PDF 导出调用 LibreOffice。依赖与技术约定分别见 `environment/` 和[计算细节](technical.md)。

## GitHub 与完整包

仓库展示项目入口、程序、图件和文档；Release 提供含全部输入与现成结果的完整 ZIP。解压完整包可以直接运行；源码克隆使用 `prepare --archive` 从已下载 ZIP 补齐完整输入，随后执行相同的校验和计算流程。
