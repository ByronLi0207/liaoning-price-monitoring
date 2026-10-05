# 数据说明

[项目首页](../README.md) · [快速开始](quickstart.md) · [项目结构](architecture.md) · [结果解读](results.md)

## 数据范围

项目分析辽宁历史农业价格监测报价，并使用国家统计局的全国价格序列提供外部参照。

| 数据部分 | 范围 | 主入口 |
| --- | --- | --- |
| 玉米与尿素县域报价 | 2018-01-05 至 2026-09-25；315 个监测日期；9,450 条记录 | `inputs/normalized_prices.csv` |
| 全国玉米与尿素价格 | 309 期流通领域重要生产资料价格记录 | `inputs/reference_experiments/data/national_prices_recovered.csv` |
| 原始网页响应 | 610 份响应；604 份成功、6 份原始 HTTP 失败 | `inputs/full_archive/data/manifest.json` |
| 更广品种档案 | 31 个精确产品／规格／单位组合；80,955 个去重单元格 | `inputs/full_archive/results/scientific_result_rates_grid_coverage.json` |

玉米与尿素面板包括 **8,987 个正值、453 个原始零值、10 个缺失值**。原始面板每期有十五个地区栏位，全期涉及十六个地区标识。核心比较固定为历史比较端点共同覆盖的十二县；另外报告剔除两个低更新县的十县、通过组合筛查的六县两组样本。

## 来源与价格口径

- 县域数据来自辽宁省发展改革委历史与现行价格监测系统。
- 全国数据来自国家统计局流通领域重要生产资料市场价格报告。
- 县域玉米使用“混等收购价”，尿素使用档案中的国产规格；原始价格单位为元／500 克。
- 标准化字段将县域报价换算为元／公斤。玉米价格除以尿素价格得到的交换比表示一公斤玉米报价金额对应的尿素公斤数。
- 全国价格单位为元／吨，外部比较使用价格变化幅度并匹配对应产品规格。

研究对象为监测系统记录的报价。数据字段分别保存原始价格、单位、记录状态和报告日期。

## 报价表怎么读

`inputs/normalized_prices.csv` 每行对应一个地区、产品和监测日期。主要字段如下：

| 字段 | 含义 |
| --- | --- |
| `region_id` / `region_name` | 地区代码和名称 |
| `date` | 标准化监测报告日期 |
| `product_id` / `specification` | 产品标识与规格 |
| `value` / `unit` | 原始报价及单位 |
| `standard_value_cny_kg` | 元／公斤报价 |
| `status` / `analysis_eligible` | 记录状态与分析使用标记 |
| `source_id` / `source_system_id` | 来源系统 |
| `raw_record_id` | 原始网页单元格的定位标识 |
| `raw_path` | 原始响应文件路径 |
| `raw_page_number` / `raw_row_number` / `raw_column_number` | 页、行、列定位 |

CSV 的 `raw_path` 相对于 `inputs/full_archive/` 解析。例如 `data/raw/example.html` 对应项目内的 `inputs/full_archive/data/raw/example.html`。响应清单保存请求日期、参数、状态、文件大小与哈希，支持从结果回到原始单元格。

## 日历与缺失处理

历史参照日历为 2018—2020 年的 **108 个日期**。后期日历为 2021—2026 年 9 月的 **207 个计划监测日期**；总体比较使用同一组 **204 个完整日期**。

报价更新比较相邻计划日期的正值记录，并要求来源系统一致。原始零值、缺失值与数据源切换分别保留状态；它们终止对应的有效相邻比较和来源内恒定报价段。

更广品种按精确产品、规格与单位组合登记。17 种常规产品具有系统性日期覆盖，其他组合的覆盖见各自记录。全国外部参照匹配玉米收购价和国产尿素；其他品种的筛查结果同时报告外部参照状态。

## 校验与引用

根目录 `MANIFEST_SHA256.json` 登记完整交付文件；使用 `python scripts/project.py verify` 核对。网页档案清单进一步登记原始响应的来源与身份信息。

使用数据时，应同时记录产品规格、县域成员、历史基准和监测日期范围。原始机构来源及相关文献列于 `reports/` 内的分析材料。随机数实现的第三方署名与许可见 `environment/LICENSE_PCG_APACHE_2.0.txt`。
