# HarnessCard

## 身份

- Harness / Scaffold 名称与版本：
- 代码 commit、镜像 digest、发布日期：
- 原生产品模式还是 locked-capability adapter：

## 控制与上下文

- system/developer prompt 及不可公开部分的哈希：
- 控制循环、planner/reviewer/verifier：
- 上下文选择、压缩、缓存和恢复策略：
- 记忆范围与跨 trial 清理方式：
- 重试、错误恢复、终止和超时规则：

## 行动面

- 工具列表、schema 和版本：
- DOM / accessibility tree / screenshot / shell / API 等观察与行动表示：
- 网络、文件系统、代码执行和凭据策略：
- 权限审批、人类介入和副作用回滚：

## 运行拓扑

- 单 Agent / 多 Agent / 子 Agent：
- 并发、委派、交接和共享状态：
- 模型路由、fallback 和 reasoning budget：

## 可观测性

- 记录的输入、输出、tool calls、环境状态、token、成本、延迟：
- Trace 中省略或脱敏的内容：
- 日志版本和保留期：

## 评测条件

- 任务集、grader、预算、trial 数和随机种子：
- benchmark-specific tuning 是否发生：
- 已知失败、不可比条件和结果适用范围：
