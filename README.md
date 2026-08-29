# AI Benchmark 与评估：从排行榜到数字员工上岗

一套面向 AI 产品负责人、Agent/Skill 工程师、FDE 与技术架构师的中文开放方法手册与实践课程（v0.3 beta）。目标不是教读者背排行榜，而是帮助读者从零设计、实现、验证并持续运营自己的 benchmark。

当前版本可用于内部课程和公开 beta：140 条来源均已登记，其中 51 条 arXiv 记录已通过一手 API 批量核验，账本共 53 条为 `verified_primary`；公平、数据劳动和在线人因等横切主题尚未形成完整专章。因此它不是“所有来源均完成学术审定的权威教材”。

## 本地阅读

需要 Node.js 22+ 与 Python 3.10+。

```bash
npm install
npm run docs:dev
```

完整质量检查：

```bash
npm test
```

`release/v0.3.2-source.sha256` 是当前 beta 的可核验源文件基线；`docs/.vitepress/dist/` 由构建生成并被忽略，不属于发布源文件。只有在审阅变更后才运行 `python3 scripts/source_manifest.py --write` 更新基线。旧版本清单保留在 `release/` 中，作为对应发布时点的历史完整性记录。

## 目录

- `docs/`：VitePress 书稿、附录和动态目录；
- `examples/commerce_supply_chain/`：电商/供应链完整案例；
- `examples/hardware_rnd/`：消费电子硬件研发完整案例；
- `templates/`：可复制的 benchmark 设计资产；
- `scripts/`：内容与链接检查；
- `.github/workflows/`：GitHub Pages 发布和质量门禁。

## 发布到 GitHub Pages

仓库启用 Pages 的 GitHub Actions 发布源后，`deploy-pages.yml` 会自动识别 project page 的仓库子路径。自定义域名或根路径部署时，可显式设置 `VITEPRESS_BASE=/`。

## 许可

- 手册正文：[CC BY-NC-SA 4.0](./LICENSE-CONTENT)
- 示例代码：[Apache License 2.0](./LICENSE-CODE)

第三方材料仍遵守各自原始许可。
