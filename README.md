# AI Benchmark 与评估：从排行榜到数字员工上岗

一本写给 AI 产品负责人、Agent/Skill 工程师、FDE 和技术架构师的中文实践手册（v0.4 beta）。它不教你背排行榜，而是带你从零做出一套能运行、能解释、还能持续维护的 benchmark。

当前版本可以用于内部课程和公开试读。书中登记了 140 条来源，其中 51 条 arXiv 记录已通过一手 API 核验，共 53 条为 `verified_primary`。公平、数据劳动和线上人机协作还没有独立成章，所以这不是一本“所有来源都已完成学术审定”的权威教材。

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

`release/v0.4.0-source.sha256` 是当前 beta 的源文件校验清单。`docs/.vitepress/dist/` 是构建产物，不属于发布源文件。审阅完变更后，运行 `python3 scripts/source_manifest.py --write` 更新当前清单；旧版本清单继续保留。

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
