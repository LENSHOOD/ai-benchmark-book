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
| 工具调用 | BFCL、ToolBench、API-Bank | 工具选择与参数生成 | 正确调用不等于业务完成 |
| Web/GUI | WebArena、OSWorld、WorkArena++ | 有状态交互与终态验证 | 环境漂移、恢复成本、表示差异 |
| 软件工程 | SWE-bench Verified、Terminal-Bench | 修改真实仓库并执行测试 | 测试质量、scaffold 与预算影响大 |
| 综合 Agent | GAIA、AgentBench、TheAgentCompany | 多工具、长程和工作任务 | 构念宽、失败归因困难 |
| 业务交互 | τ-bench、CRMArena-Pro、AutomationBench | 政策、连续可靠性和 SaaS 工作流 | 公开数据难代表企业私有流程 |
| Skill | SkillsBench、SWE-Skills-Bench | Skill 的平均与任务级增益 | 发现、冲突、过期与负迁移 |
| 工作价值 | GDPval、SWE-Lancer | 真实工作产物和经济任务 | 专家基线与完整岗位外推有限 |
| 安全 | AgentDojo、WASP、ToolSandbox | 提示注入、工具安全与隔离 | 攻击覆盖与现实威胁持续变化 |

<a :href="withBase('/downloads/benchmark_catalog.csv')" download>下载完整 70 项结构化目录</a>。CSV 中的 `maturity` 只是本书在 2026-08-27 快照里使用的粗略编辑标签，取值为 `foundational`、`established` 和 `evolving`。它不代表项目口碑，也不是项目官方状态。

`active / audited / saturated / revised / retired` 是下一版准备加入的生命周期字段。本版还没有逐项补齐版本和复核日期，所以不声称已经实现这套机制。站点也发布了 <a :href="withBase('/downloads/sources.jsonl')" download>JSONL 来源账本</a>。其中 `unverified` 的意思是“元数据还没逐条核验”，不是“已经验证”。

> 移动端可横向滑动下表；结构化 CSV 更适合筛选和二次分析。

> [!WARNING]
> 不要从 Radar 的项目数量推断领域成熟度。一个有 20 个相似静态题集的领域，未必比只有一个可执行环境的领域更接近真实部署。
