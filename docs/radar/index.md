---
title: Benchmark Radar
description: 代表性 benchmark 的用途、状态与已知边界
---

<script setup>
import { withBase } from 'vitepress'
</script>

# Benchmark Radar

Radar 不是又一张排行榜。它只帮你快速回答三个问题：这个项目测什么，适合拿来做什么决定，已知短板是什么。

| 层级 | 代表项目 | 主要用途 | 典型限制 |
|---|---|---|---|
| 基础模型 | MMLU、HELM、C-Eval、CMMLU | 知识、推理、多指标诊断 | 污染、饱和、格式与岗位错配 |
| 工具调用 | BFCL、ToolBench、API-Bank、ToolSandbox | 工具选择、参数与有状态工具交互 | 正确调用不等于业务完成 |
| Web/GUI | WebArena、OSWorld、WorkArena++ | 有状态交互与终态验证 | 环境漂移、恢复成本、表示差异 |
| 软件工程与终端 | SWE-bench Verified、Terminal-Bench | 仓库修复与终端任务，按环境测试验收 | 测试质量、scaffold 与预算影响大 |
| 综合 Agent | GAIA、AgentBench、TheAgentCompany | 多工具、长程和工作任务 | 构念宽、失败归因困难 |
| 业务交互 | τ-bench、CRMArena-Pro、AutomationBench | 政策、连续可靠性和 SaaS 工作流 | 公开数据难代表企业私有流程 |
| Skill | SkillsBench、SWE-Skills-Bench | Skill 的平均与任务级增益 | 发现、冲突、过期与负迁移 |
| 工作价值 | GDPval、SWE-Lancer | 真实工作产物和经济任务 | 专家基线与完整岗位外推有限 |
| 安全 | AgentDojo、WASP | 提示注入、工具安全与隔离 | 攻击覆盖与现实威胁持续变化 |

<a :href="withBase('/downloads/benchmark_catalog.csv')" download>下载完整 84 项结构化目录</a>。`maturity` 是编辑标签，取值为 `foundational`、`established` 和 `evolving`，不代表口碑或项目官方状态。原70项快照保留，9月补入14项；其中部分是更早发布、这次补查到的项目。

新增条目记录 `version`、`last_verified`、`verification_scope` 和 `update_kind`。旧条目的这些字段可能为空，不能据整份目录日期推断它们都已重核。`new_in_window` 表示8月29日至9月19日的新工作；`earlier_omission` 表示较早资料的补录。

`active / audited / saturated / revised / retired` 生命周期仍未逐项实施。站点提供 <a :href="withBase('/downloads/sources.jsonl')" download>来源账本</a>，`unverified` 表示元数据待核验；`verified_primary` 也不等于独立复现了结果。

> 移动端可横向滑动上表；结构化 CSV 更适合筛选和二次分析。

## 2026年9月增量：哪些会改变评测设计

| 新材料 | 设计问题 | 如何放进本书 |
|---|---|---|
| [τ^τ-Bench](https://arxiv.org/html/2609.04611v1)，9月4日 | 从客户资料构建可用Agent，而不只操作现成Agent | 第12章；模拟客户、隐藏验收与服务预算 |
| [EvoHarnessBench v2](https://arxiv.org/html/2609.04280v2)，9月10日 | 增加工具或Skill后，旧任务会不会退步 | 第9章；分阶段保留与适应 |
| [READY](https://arxiv.org/html/2609.02095v1)，9月2日 | 多少人工复核，才能以可接受成本达标 | 第15章；固定策略后用资格集验证，注明人审假设 |
| [GAUGE](https://arxiv.org/html/2609.12191v1)，9月10日 | 总体排序像人，能否可靠地区分相近候选 | 第6章；业务真值、局部误判和主观满意度分开 |
| [RePro](https://arxiv.org/html/2609.00062v1)，8月30日 | 改写新题时如何验证题目和答案 | 第5章；形式化证明不能代替自然语言语义核对 |
| [HLS-Eval Agent扩展](https://arxiv.org/html/2609.09526v1)，9月8日上传 | 硬件设计怎样把编译、仿真、迭代与成本一起测 | 第14章；简单内核的pass@10不等于整机研发可靠性 |
| [AREAs-Lab](https://arxiv.org/abs/2608.28979)，8月29日 | 系统会不会问出缺失需求 | FDE延伸阅读；需求与用户均有合成边界 |
| [SANE](https://openreview.net/forum?id=q2kabbh38L)，9月11日提交 | 如何针对裁判目标自动生成反例 | 第6章；截至复核日仍在TMLR审稿 |

### 新近传播与首次发布不是一回事

[Terminal-Bench 4.0](https://www.tbench.ai/news/terminal-bench-4-0) 是8月28日的维护版本，因题目和资源条件改变而要求重跑。[CEO-Bench](https://ceobench.com/) 官网标为6月；其最佳轨迹不能代替平均成绩。[ARC-AGI-3](https://arcprize.org/competitions/2026/arc-agi-3) 也属于较早的交互任务，不能因为9月讨论热就写成新首发。

另外，[Agentic Skills at Scale](https://arxiv.org/abs/2606.17819) 从Skill内容构造任务，适合单项Skill维护，不代表生产频率分布。[ClawBench](https://github.com/TIGER-AI-Lab/ClawBench) 展示实时网站、语料版本和评分口径的关系。它们进入补录区，不用一个项目数量替代领域成熟度判断。

### 两份可以借鉴、但不能当独立ROI证明的实践

[NVIDIA供应链案例](https://developer.nvidia.com/blog/from-wafer-out-to-first-token-codifying-supply-chain-expertise-with-nemotron-and-palantir-foundry/) 在9月10日描述历史时点回放与计划员决策，指标来自厂商开发评测。[Netflix Judge生命周期](https://netflixtechblog.medium.com/the-lifecycle-of-llm-as-a-judge-building-aligning-and-monitoring-at-scale-c95bd8283508) 于9月4日介绍标签、理由和持续人工复查。两者均应保留场景和证据边界。

> [!WARNING]
> 不要从 Radar 的项目数量推断领域成熟度。一个有 20 个相似静态题集的领域，未必比只有一个可执行环境的领域更接近真实部署。
