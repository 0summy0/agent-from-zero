import { defineConfig } from 'vitepress'

const zhChapters = [
  ['1.1 Tokenizer', '/zh/1.1-tokenizer'],
  ['1.2 采样：温度与 top-p', '/zh/1.2-sampling'],
  ['1.3 上下文窗口与注意力', '/zh/1.3-attention'],
  ['1.4 幻觉与证据', '/zh/1.4-hallucination'],
  ['2.1 结构化输出', '/zh/2.1-structured-output'],
  ['2.2 工具调用', '/zh/2.2-tool-calling'],
  ['2.3 ReAct 循环', '/zh/2.3-react-loop'],
  ['2.4 记忆与上下文', '/zh/2.4-memory-context'],
  ['2.5 MCP', '/zh/2.5-mcp'],
  ['2.6 Agent Skills', '/zh/2.6-agent-skills'],
  ['3.1 评测', '/zh/3.1-evaluation'],
  ['3.2 追踪与可观测性', '/zh/3.2-tracing'],
  ['3.3 安全', '/zh/3.3-security'],
  ['3.4 成本与延迟', '/zh/3.4-cost-latency'],
  ['4.1 多智能体', '/zh/4.1-multi-agent'],
  ['4.2 浏览器使用', '/zh/4.2-browser-use'],
  ['4.3 实时语音', '/zh/4.3-realtime-voice'],
  ['4.4 毕业项目', '/zh/4.4-capstone'],
]

const enChapters = [
  ['1.1 Tokenizer', '/en/1.1-tokenizer'],
  ['1.2 Sampling', '/en/1.2-sampling'],
  ['1.3 Context and Attention', '/en/1.3-attention'],
  ['1.4 Hallucination and Evidence', '/en/1.4-hallucination'],
  ['2.1 Structured Outputs', '/en/2.1-structured-output'],
  ['2.2 Tool Calling', '/en/2.2-tool-calling'],
  ['2.3 ReAct Loop', '/en/2.3-react-loop'],
  ['2.4 Memory and Context', '/en/2.4-memory-context'],
  ['2.5 MCP', '/en/2.5-mcp'],
  ['2.6 Agent Skills', '/en/2.6-agent-skills'],
  ['3.1 Evaluation', '/en/3.1-evaluation'],
  ['3.2 Tracing', '/en/3.2-tracing'],
  ['3.3 Security', '/en/3.3-security'],
  ['3.4 Cost and Latency', '/en/3.4-cost-latency'],
  ['4.1 Multi-Agent Systems', '/en/4.1-multi-agent'],
  ['4.2 Browser Use', '/en/4.2-browser-use'],
  ['4.3 Realtime Voice', '/en/4.3-realtime-voice'],
  ['4.4 Capstone', '/en/4.4-capstone'],
]

const sidebar = (chapters: string[][]) => [
  {
    text: '课程章节 / Chapters',
    collapsed: false,
    items: chapters.map(([text, link]) => ({ text, link })),
  },
]

export default defineConfig({
  lang: 'zh-CN',
  title: 'Agent From Zero',
  description: '双语零基础 AI Agent 课程：每章代码都由 CI 真实执行。',
  base: '/agent-from-zero/',
  srcDir: 'docs',
  cleanUrls: true,
  lastUpdated: false,
  themeConfig: {
    nav: [
      { text: '中文课程', link: '/zh/1.1-tokenizer' },
      { text: 'English', link: '/en/1.1-tokenizer' },
      { text: '毕业项目', link: '/zh/4.4-capstone' },
      { text: 'GitHub', link: 'https://github.com/0summy0/agent-from-zero' },
    ],
    sidebar: {
      '/zh/': sidebar(zhChapters),
      '/en/': sidebar(enChapters),
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/0summy0/agent-from-zero' },
    ],
    search: {
      provider: 'local',
    },
    outline: { level: [2, 3], label: '本页目录' },
    docFooter: { prev: '上一章', next: '下一章' },
    editLink: {
      pattern: 'https://github.com/0summy0/agent-from-zero/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页',
    },
  },
})
