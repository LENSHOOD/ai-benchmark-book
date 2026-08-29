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

仓库 `templates/` 提供七项可复制资产。模板不是文档交付清单，而是迫使团队在运行前做出关键决定。

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

先写 Charter，再做流程与任务宇宙。不要先填 Task Spec，因为手头案例会反过来定义构念。环境和 Harness 初步确定后写 Harness Card；grader 必须与 Task Spec 同时测试；Release Gate 在看资格结果前签字。

## 模板完成的判断

两位未参与编写的领域专家能否独立判断任务通过？工程师能否依据文档重置环境、运行候选和解释失败？决策者能否知道某分数不足时应该拒绝、补证还是缩权？若不能，模板仍只是文字。

## 下载

VitePress 会将仓库源文件一同发布在 GitHub。也可以直接复制 `templates/` 目录到自己的项目；其中企业字段只是示例，可在不改变核心证据链的前提下扩展。
