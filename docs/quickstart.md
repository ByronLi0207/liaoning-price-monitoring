# 快速开始

[中文首页](../README_zh.md) · [English](../README.md) · [图表复现映射](replication_map.md) · [数据说明](data.md) · [结果解读](results.md)

## 1. 获取完整项目

[完整项目 ZIP](https://github.com/ByronLi0207/liaoning-price-monitoring/releases/latest/download/agri-price-monitor.zip) 包含源代码、全部分析输入、现成结果和图件。解压后进入 `agri-price-monitor` 目录，以下命令均从该目录运行。

源码仓库包含分析程序、reports中的论文与补充资料、独立图件和项目文档。**inputs完整数据与results完整参照输出位于完整 Release 附件**；GitHub自动生成的源码ZIP对应跟踪文件。存档系列 DOI 为 [10.5281/zenodo.23131960](https://doi.org/10.5281/zenodo.23131960)。选择克隆源码时，先下载完整附件，再运行：

```bash
python scripts/project.py prepare --archive /path/to/agri-price-monitor.zip
```

`/path/to/agri-price-monitor.zip` 替换为实际下载路径。路径包含空格时，用引号包住完整路径。

## 2. 查看项目并检查文件

```bash
python scripts/project.py info
python scripts/project.py verify
```

这两个命令使用 Python 标准库。`info` 显示项目用途、数据范围与主要目录；`verify` 对照 `MANIFEST_SHA256.json` 检查交付文件的路径、大小和 SHA-256。先完成检查，再运行完整计算。

## 3. 配置计算环境

参照计算环境为 **Python 3.12.14、Node.js 24.19.0**。这些版本标识用于记录运行环境，不要求当前版本与其逐字一致。Python 依赖版本见 [`requirements.lock.txt`](../environment/requirements.lock.txt)，完整环境记录见 [`runtime.json`](../environment/runtime.json)。

建议在独立环境安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r environment/requirements.lock.txt
```

Windows PowerShell 的激活命令为 `.venv\Scripts\Activate.ps1`。系统命令为 `python3` 时，将命令中的 `python` 替换为 `python3`。

季节性结果中的 Python 和 NumPy 版本只记入环境比较记录；Node 和平台版本只记入运行回执。输入哈希、方法哈希、计数、日期分类及计算参数继续严格核验，科学结果有实质变化时仍会失败。固定依赖用于重建已测试环境，版本信息差异本身不会触发科学验收失败。

确认 Python 和 Node.js 都能从命令行启动：

```bash
python --version
node --version
```

若 Node.js 安装在自定义位置，可用环境变量 `NODE` 指定其可执行文件。分析输入已包含在项目中，计算阶段无需再次获取价格数据。

## 4. 重建计算结果

```bash
python scripts/project.py reproduce
```

完整流程包括：

1. 核对重抽样索引、基准系数与计数参照文件。
2. 重建五个历史基准、三组县域样本、三种块长的 45 组比较。
3. 运行六项 9,999 次抽样的精度检查和逐日预警回放。
4. 重算低于基准的持续段与报价更新统计。
5. 解析 610 份网页响应，整理更广品种的覆盖和筛查记录。
6. 生成四张独立图件并构建可编辑分析材料。

主要输出位置：

| 路径 | 用途 |
| --- | --- |
| `reproduction/workspace/results/primary_15_L6.json` | 五基准 × 三县域样本的主比较 |
| `reproduction/workspace/results/precision/` | 六项精度检查、抽样索引、系数与计数结果 |
| `reproduction/workspace/results/alerts/` | 每个监测日期的预警分类与汇总 |
| `reproduction/workspace/figures/` | 独立 PNG 和 PDF 图件 |
| `reproduction/workspace/` | 隔离运行的完整工作副本和重新计算的结果 |
| `native/` | 重新构建的 Word 文件 |
| `reproduction/` | 本次执行日志与运行汇总 |

成功完成时，终端输出包含 `"status": "PASS"` 的汇总。步骤报错时，按终端提示查看 `reproduction/` 中对应日志。

输入、现成结果、图件和报告的原文件保持不变。文件校验检查下载材料的 SHA-256；复现检验分别检查科学数值、整数、分类和缺失状态。浮点数按绝对阈值 10⁻¹² 加相对阈值 10⁻¹² 比较，并报告实际最大差值；计数、分类和抽样索引逐项精确一致。图片核对统计输入和尺寸，跨系统的图片编码差异不作为科学结果错误。再次完整运行前，将现有 `reproduction/` 移到其他位置，避免混合两次输出。

## 5. 导出 PDF

导出使用 **LibreOffice**，并需要 Liberation Serif 及相应数学符号字体。在完成计算和文档构建后运行：

```bash
python scripts/project.py export
```

`SOFFICE` 环境变量可指定 LibreOffice 可执行文件。导出 PDF 和逐页 PNG 位于：

- `native/render_manuscript_reproduced/`；
- `native/render_supplement_reproduced/`。

随项目提供的现成分析材料位于 `reports/`，重新生成的材料位于 `native/`。PDF 的文字、表格、公式和页面显示可与现成材料直接对照。

## 命令速查

| 操作 | 项目命令 |
| --- | --- |
| 查看概况 | `python scripts/project.py info` |
| 校验交付文件 | `python scripts/project.py verify` |
| 为源码补齐完整输入 | `python scripts/project.py prepare --archive /path/to/agri-price-monitor.zip` |
| 重建计算与图件 | `python scripts/project.py reproduce` |
| 导出 PDF | `python scripts/project.py export` |

同一组操作也可通过项目根目录的 `Makefile` 调用。Table 1–4、Figure 1–2的负责命令、真实输入和结果文件见[图表复现映射](replication_map.md)；计算定义与数值约定见[计算细节](technical.md)。

## 补充检验

统一复现入口同时运行全部县的对称删除、2018—2020 年筛查与两个后期窗口验证、以及同品种其他十一县对照。对应结果位于 `results/supplementary_validation/`，结果报告位于 `reports/supplement_validation.pdf`。完整实验设计及汇总见该报告；机器精度结果可从 JSON/CSV 读取。

## Chinese brief export

The package supplies the OFL-licensed Agri Serif SC font under `assets/fonts/`. The PDF export command discovers it through the project font configuration; no font installation is required for that command. Install the supplied font to edit the Chinese brief in desktop Word using the same typeface.
