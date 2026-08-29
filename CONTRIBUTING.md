# 贡献指南

欢迎提交勘误、新 benchmark 条目、行业扩展和代码修复。事实性新增内容应提供原始来源；不要仅引用聚合排行榜或二手转述。

提交前运行：

```bash
npm test
```

内容贡献请标明属于事实、综合判断、实践建议、合成案例还是未来推测。Benchmark Radar 的新条目还需包含版本、发布日期、被测对象、任务形态、grader、已知限制和项目链接。

GitHub Pages 由 CI 从 `docs/` 构建。`docs/.vitepress/dist/` 是可丢弃且被忽略的本地产物，不提交为发布源；当前版本基线由 `release/v0.3.2-source.sha256` 记录。源文件修改完成并经人工审阅后，维护者应在提交 PR 前运行 `python3 scripts/source_manifest.py --write`，将重建后的当前版本清单与变更一并提交，再以 `npm test` 做最终验证。旧版本清单不得覆盖。
