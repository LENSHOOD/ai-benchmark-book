---
title: 模板使用指南
---

<script setup>
import { withBase } from 'vitepress'
</script>

# 模板使用指南

所有模板均可直接下载：

- <a :href="withBase('/downloads/templates/benchmark_charter.md')" download>Benchmark Charter</a>
- <a :href="withBase('/downloads/templates/fde_process_inventory.csv')" download>FDE 流程盘点表</a>
- <a :href="withBase('/downloads/templates/harness_card.md')" download>Harness Card</a>
- <a :href="withBase('/downloads/templates/incident_to_eval.md')" download>Incident to Eval</a>
- <a :href="withBase('/downloads/templates/release_gate.md')" download>Release Gate</a>
- <a :href="withBase('/downloads/templates/rubric_and_judge_card.md')" download>Rubric & Judge Card</a>
- <a :href="withBase('/downloads/templates/task_spec.yaml')" download>Task Spec YAML</a>

仓库 `templates/` 提供七份可以直接改的模板。它们不是为了凑文档，而是逼团队在开跑之前把关键问题说清楚。

| 模板 | 使用时机 | 最重要的问题 |
|---|---|---|
| `benchmark_charter.md` | 项目立项 | 分数最终支持哪个决策？ |
| `fde_process_inventory.csv` | 流程发现 | 哪个窄切片最适合第一轮？ |
| `task_spec.yaml` | 写题 | 初始、目标、禁止与升级是否可独立判断？ |
| `harness_card.md` | 固定被测系统 | 除模型外哪些机制改变结果？ |
| `rubric_and_judge_card.md` | 设计开放评分 | Judge 在阈值附近怎样失效？ |
| `release_gate.md` | 资格运行前 | 什么条件通过、缩权或拒绝？ |
| `incident_to_eval.md` | 生产事故后 | 如何将事实重建成最小可复现回归？ |

## 推荐顺序

先写 Charter，明确要支持什么决定，再盘点流程和任务范围。不要一上来就填 Task Spec，否则手边几个案例会反过来限制你想测的能力。环境和 Harness 初步确定后再写 Harness Card。任务和评分器要一起测试，发布门禁要在看资格结果之前签字。

## 模板完成的判断

找两位没参与编写的领域专家。他们能否独立判断任务是否通过？工程师能否只看文档就重置环境、运行候选并解释失败？决策者看到证据不足时，是否知道应该拒绝、补证还是缩权？如果不能，这些模板还只是文字。

## 下载

VitePress 会将仓库源文件一同发布在 GitHub。也可以直接复制 `templates/` 目录到自己的项目；其中企业字段只是示例，可在不改变核心证据链的前提下扩展。
