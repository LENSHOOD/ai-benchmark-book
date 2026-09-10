# 贡献指南

欢迎提交勘误、新 benchmark 条目、行业扩展和代码修复。事实性新增内容应提供原始来源；不要仅引用聚合排行榜或二手转述。

提交前运行：

```bash
npm test
```

内容贡献请标明属于事实、综合判断、实践建议、合成案例还是未来推测。Benchmark Radar 的新条目还需包含版本、发布日期、被测对象、任务形态、grader、已知限制和项目链接。

GitHub Pages 由 CI 从 `docs/` 构建。`docs/.vitepress/dist/` 是本地构建产物，不要提交。当前版本清单是 `release/v0.4.0-source.sha256`。源文件改完并审阅后，在提交 PR 前运行 `python3 scripts/source_manifest.py --write`，把新清单和内容一起提交，再用 `npm test` 做最终检查。不要覆盖旧版本清单。
