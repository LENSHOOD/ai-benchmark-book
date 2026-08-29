import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createMarkdownRenderer } from 'vitepress'

const here = path.dirname(fileURLToPath(import.meta.url))
const input = path.join(here, 'INDEPENDENT_REVIEW_REPORT.md')
const output = path.join(here, 'INDEPENDENT_REVIEW_REPORT.html')
const source = fs.readFileSync(input, 'utf8').replace(/^---\n[\s\S]*?\n---\n/, '')
const md = await createMarkdownRenderer(here, { lineNumbers: false }, '/')
let body = await md.render(source)
body = body.replace(/<h2([^>]*)>/g, '<h2 class="section-title"$1>')
body = body.replace(/(<h2 class="section-title"[^>]*>)([\s\S]*?)(<\/h2>)/g, (_match, open, content, close) => `${open}${content.replace(/\s*<a class="header-anchor"[\s\S]*?<\/a>/, '')}${close}`)
body = body.replace(/<h2 class="section-title"[^>]*>/g, '<h2 class="section-title">')
body = body.replace(/<p>\[(\d+)\]\s*/g, '<p class="bib-entry"><span class="bib-number">[$1]</span> ')
body = body.replace(/href="\.\/(review_protocol|chapter_matrix|issue_register)\.html"/g, 'href="./$1.md"')
const bibliographyAt = body.indexOf('<h2 class="section-title">Bibliography')
if (bibliographyAt !== -1) {
  body = `${body.slice(0, bibliographyAt)}<section class="bibliography">${body.slice(bibliographyAt)}</section>`
}

const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>《AI Benchmark 与评估》v0.1.0 独立完整审查报告</title>
<style>
  :root { --ink:#18242b; --navy:#123f52; --cyan:#0f7189; --paper:#fff; --soft:#eef5f6; --line:#cddadd; --major:#a33b2b; }
  * { box-sizing:border-box; }
  html { background:#edf1f2; }
  body { margin:0; color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; line-height:1.72; }
  .header { background:linear-gradient(135deg,#0d3445,#176277); color:white; padding:48px max(7vw,32px) 36px; }
  .header .kicker { letter-spacing:.12em; text-transform:uppercase; font-size:12px; opacity:.75; }
  .header h1 { max-width:1050px; margin:12px 0 18px; font-size:clamp(28px,4vw,48px); line-height:1.2; }
  .header .meta { display:flex; flex-wrap:wrap; gap:20px; font-size:13px; color:#c7e5ea; }
  .metrics { display:grid; grid-template-columns:repeat(4,minmax(120px,1fr)); background:white; border-bottom:1px solid var(--line); }
  .metric { padding:20px; text-align:center; border-right:1px solid var(--line); }
  .metric strong { display:block; color:var(--navy); font-size:29px; line-height:1.1; }
  .metric span { display:block; margin-top:5px; color:#536970; font-size:12px; }
  main { max-width:1100px; margin:0 auto; padding:48px 48px 80px; background:var(--paper); }
  h1:first-child { display:none; }
  h2 { margin:45px 0 18px; padding-bottom:8px; color:var(--navy); border-bottom:2px solid var(--navy); font-size:25px; }
  h3 { margin:32px 0 12px; color:var(--navy); font-size:19px; }
  h4 { color:var(--navy); }
  p { margin:0 0 15px; }
  a { color:var(--cyan); text-decoration-thickness:1px; text-underline-offset:2px; }
  code { padding:2px 5px; background:var(--soft); border-radius:4px; font-family:"SFMono-Regular",Consolas,monospace; font-size:.9em; }
  table { width:100%; border-collapse:collapse; margin:18px 0 28px; font-size:13px; }
  th { background:var(--navy); color:white; text-align:left; padding:10px 12px; }
  td { padding:10px 12px; border-bottom:1px solid var(--line); vertical-align:top; }
  tr:nth-child(even) td { background:#f7fafb; }
  blockquote { margin:20px 0; padding:14px 18px; background:var(--soft); border-left:4px solid var(--cyan); }
  li { margin:7px 0; }
  strong { color:#102f3b; }
  @media (max-width:720px) { .metrics{grid-template-columns:repeat(2,1fr)} main{padding:30px 20px 60px} table{display:block;overflow-x:auto} }
  @media print {
    @page { size:A4; margin:16mm 15mm 18mm; }
    html,body { background:white; font-size:10.2pt; }
    .header { margin:-16mm -15mm 0; padding:28mm 18mm 18mm; break-after:page; }
    .metrics { display:none; }
    main { max-width:none; padding:0; }
    h2 { break-after:avoid; margin-top:24px; font-size:17pt; }
    h3 { break-after:avoid; font-size:13pt; }
    table { break-inside:auto; font-size:8.4pt; }
    tr { break-inside:avoid; }
    a { color:inherit; text-decoration:none; }
  }
</style>
</head>
<body>
<header class="header">
  <div class="kicker">Independent content, evidence and implementation review</div>
  <h1>《AI Benchmark 与评估》v0.1.0 独立完整审查报告</h1>
  <div class="meta"><span>审查日期：2026-08-23</span><span>冻结版本：v0.1.0</span><span>结论：Beta 可用 / v1.0 No-Go</span></div>
</header>
<section class="metrics" aria-label="审查摘要">
  <div class="metric"><strong>16</strong><span>逐章审查</span></div>
  <div class="metric"><strong>121</strong><span>来源健康检查</span></div>
  <div class="metric"><strong>70</strong><span>Radar 全量审计</span></div>
  <div class="metric"><strong>6</strong><span>Major 发布阻断项</span></div>
</section>
<main class="content">${body}</main>
</body>
</html>`

fs.writeFileSync(output, html)
console.log(output)
