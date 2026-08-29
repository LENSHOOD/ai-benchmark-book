import { defineConfig } from 'vitepress'

const base = process.env.VITEPRESS_BASE || '/'

export default defineConfig({
  lang: 'zh-CN',
  title: 'AI Benchmark 与评估',
  description: '从历史、测量原理和系统框架，到企业数字员工的可运行评测实践',
  base,
  cleanUrls: true,
  lastUpdated: true,
  head: [
    ['meta', { name: 'theme-color', content: '#153f52' }],
    ['link', { rel: 'icon', href: `${base}logo.svg`, type: 'image/svg+xml' }]
  ],
  markdown: {
    math: true,
    lineNumbers: true,
    headers: { level: [2, 3] }
  },
  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'AI Benchmark 与评估',
    outline: { level: [2, 3], label: '本页目录' },
    lastUpdated: { text: '最后更新' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    returnToTopLabel: '返回顶部',
    sidebarMenuLabel: '目录',
    darkModeSwitchLabel: '外观',
    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索', buttonAriaLabel: '搜索' },
          modal: {
            noResultsText: '没有找到相关内容',
            resetButtonTitle: '清除查询',
            footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' }
          }
        }
      }
    },
    nav: [
      { text: '开始阅读', link: '/start/' },
      { text: '正文', link: '/book/01-why-eval' },
      { text: '实践', link: '/labs/' },
      { text: 'Benchmark Radar', link: '/radar/' },
      { text: '变更记录', link: '/changelog' },
      { text: '附录', link: '/appendix/glossary' }
    ],
    sidebar: [
      {
        text: '阅读之前',
        items: [
          { text: '阅读指南', link: '/start/' },
          { text: '全书地图', link: '/start/map' },
          { text: '如何使用案例与代码', link: '/labs/' }
        ]
      },
      {
        text: '第一部分 · 为什么评测',
        collapsed: false,
        items: [
          { text: '01 为什么评测决定 AI 能走多远', link: '/book/01-why-eval' },
          { text: '02 从心理测量到动态 Agent Eval', link: '/book/02-history' },
          { text: '03 Eval、Benchmark 与排行榜', link: '/book/03-language' }
        ]
      },
      {
        text: '第二部分 · 测量原理',
        items: [
          { text: '04 构念、效度、信度与分数', link: '/book/04-measurement' },
          { text: '05 从任务宇宙到可维护题集', link: '/book/05-task-universe' },
          { text: '06 Grader、人类与 LLM Judge', link: '/book/06-graders' }
        ]
      },
      {
        text: '第三部分 · 系统评测',
        items: [
          { text: '07 基础模型评测的正确读法', link: '/book/07-models' },
          { text: '08 Agent 与环境状态评测', link: '/book/08-agents' },
          { text: '09 Harness：被忽略的系统变量', link: '/book/09-harness' },
          { text: '10 Skill/Plugin：可验证干预', link: '/book/10-skills' },
          { text: '11 实验、统计与因果归因', link: '/book/11-experiments' }
        ]
      },
      {
        text: '第四部分 · 企业实践',
        items: [
          { text: '12 企业 Benchmark 与 FDE', link: '/book/12-enterprise-fde' },
          { text: '13 电商与供应链端到端设计', link: '/book/13-commerce-supply-chain' },
          { text: '14 智能硬件研发端到端设计', link: '/book/14-hardware-rnd' }
        ]
      },
      {
        text: '第五部分 · 治理与未来',
        items: [
          { text: '15 上岗、授权、复证与治理', link: '/book/15-governance' },
          { text: '16 评测评测本身，以及未来', link: '/book/16-future' }
        ]
      },
      {
        text: '参考与工具',
        items: [
          { text: 'Benchmark Radar', link: '/radar/' },
          { text: '术语表', link: '/appendix/glossary' },
          { text: '统计速查', link: '/appendix/statistics' },
          { text: '框架总览', link: '/appendix/framework-map' },
          { text: '模板使用指南', link: '/appendix/templates' },
          { text: '练习参考答案', link: '/appendix/answers' },
          { text: '参考文献', link: '/appendix/references' },
          { text: '方法与边界', link: '/appendix/methodology' }
        ]
      }
    ],
    footer: {
      message: '正文 CC BY-NC-SA 4.0 · 代码 Apache-2.0',
      copyright: '证据复核至 2026-08-28 · v0.3.2 beta'
    }
  }
})
