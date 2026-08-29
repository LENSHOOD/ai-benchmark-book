---
title: 实践环境
---

# 实践环境

本书提供两套完全本地的参考实现：

| 项目 | 主要环境 | 关键风险 | 入口 |
|---|---|---|---|
| 云舟零售履约异常 | 订单、库存、物流、退款和审批 | 越权拆单、错退款、重复动作、未升级 | `examples/commerce_supply_chain/` |
| 星桥硬件研发门禁 | 需求、BOM、测试、缺陷和工程变更 | 无证据放行、危险替代料、漏掉安全缺陷 | `examples/hardware_rnd/` |

在仓库根目录运行：

```bash
python3 -m unittest discover -s examples -p 'test_*.py' -v
python3 examples/run_all.py
```

默认“模型”是可复现的规则策略替身，不读取 grader 的目标状态或答案字段。受控 seed 会注入请求前失败、部分写入、响应丢失与服务不可用；Workflow 条件必须用幂等查询和安全重试恢复。它的成绩是教学信号，只证明运行器、任务、环境与 grader 的数据链能够鉴别一些已定义的变异。接入真实模型后，仍必须记录 provider、模型快照、推理参数、预算、重试和完整输出。

## 贯穿练习

每章练习都会产出一个项目工件。依次完成后，你将得到：Benchmark Charter、构念图、任务清单、Task Spec、Grader Card、Harness Card、实验预注册、发布门禁和复证计划。

## Lab 1：证明答案没有泄漏（15 分钟）

**目标**：理解 SUT 与 grader 的隔离边界。运行全套测试，然后打开 `examples/test_benchmark_core.py`。该测试先让策略产生一次输出，再把私有 `target_state` 改成不可能值；策略输出不变而 grader 失败，说明策略不是照抄答案键。

```bash
python3 -m unittest examples.test_benchmark_core -v
```

**预期产物**：一段说明，列出 `PublicTask` 可见字段、`Task` 私有字段和你自己的系统中相应边界。若被测函数仍接收 gold、rubric 答案或 required actions，本 Lab 未通过。

## Lab 2：检查状态、veto 与替代路径（30 分钟）

**目标**：验证 grader 不奖励漂亮声明，也不强迫唯一轨迹。选择 `cs-004` 或 `hw-003`，构造三种输出：不同路径但正确终态；近错终态；危险捷径。运行 `grade()`，预期依次为 pass、fail、veto。

**自检**：替代路径没有因为 action 名不同被拒绝；危险动作即使其他分数很高仍为零；缺少目标状态不能被证据文本补偿。

## Lab 3：观察四类工具故障（半天）

**目标**：理解多 trial 为什么必须改变真实执行。`StatefulEnvironment` 用 seed 选择 `pre_call`、`partial_write`、`response_lost`、`unavailable` 或无故障。对同一候选与任务打印 trace，比较 Direct 与 Workflow：前者可能留下不确定写入，后者先查询幂等状态；永久不可用必须成为证据不足。

**预期产物**：故障类型—正确响应表、两条代表 trace 和一个你新增的恢复测试。不得把环境不可用改记为模型答错来让报表更简单。

## Lab 4：任务级配对而非伪重复（30 分钟）

运行两个 suite，检查 `paired_tasks`、`total_trials` 与 `ci95`：

```bash
python3 examples/commerce_supply_chain/run.py
python3 examples/hardware_rnd/run.py
```

每套有 10 个任务、每候选 4 次 trial。比较函数报告 10 个配对任务和两候选合计 80 条 trial，而不是把 40 次候选运行称为 40 个独立配对样本。将 trial 数改成 2，`paired_tasks` 应保持 10。

## Lab 5：生成可复现运行包（15 分钟）

```bash
python3 examples/run_all.py
```

命令在 `examples/results/` 下创建两个不可覆盖目录。检查 `run_manifest.json` 是否含 suite/grader 版本、任务/候选/seed 数和产生方差的单元数；检查逐 trial 记录是否含 seed、环境 hash、failure class、成本、延迟、trace 和证据不足。第二次运行不得覆盖第一次结果。

## Lab 6：把一个业务流程移植进来（一周工作坊）

使用[模板指南](/appendix/templates)完成 Charter、Task Spec、Grader Card 与 Release Gate。至少取一个真实顺利案例、一个多次交接案例和一个事故/险情，生成正常、近错、缺证据和工具故障题族。让另一位同事在不询问出题者的情况下复跑；所有无法解释的字段或判断进入问题台账，而不是由作者口头补充。
