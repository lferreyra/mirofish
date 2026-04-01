export default {
  common: {
    start: '开始',
    back: '返回',
    next: '下一步',
    cancel: '取消',
    confirm: '确认',
    upload: '上传',
    download: '下载',
    delete: '删除',
    save: '保存',
    edit: '编辑',
    view: '查看',
    loading: '加载中...',
    processing: '处理中',
    completed: '已完成',
    error: '错误',
    success: '成功',
    status: '状态',
    settings: '设置',
    help: '帮助',
    about: '关于'
  },
  home: {
    nav: {
      github: '访问我们的Github主页'
    },
    hero: {
      tag: '简洁通用的群体智能引擎',
      version: '/ v0.1-预览版',
      title: '上传任意报告',
      titleHighlight: '即刻推演未来',
      desc: '即使只有一段文字，<span class="highlight-bold">MiroFish</span> 也能基于其中的现实种子，全自动生成与之对应的至多<span class="highlight-orange">百万级Agent</span>构成的平行世界。通过上帝视角注入变量，在复杂的群体交互中寻找动态环境下的<span class="highlight-code">"局部最优解"</span>',
      slogan: '让未来在 Agent 群中预演，让决策在百战后胜出<span class="blinking-cursor">_</span>'
    },
    systemStatus: {
      title: '系统状态',
      ready: '准备就绪',
      readyDesc: '预测引擎待命中，可上传多份非结构化数据以初始化模拟序列',
      metrics: {
        lowCost: '低成本',
        lowCostDesc: '常规模拟平均5$/次',
        highAvailability: '高可用',
        highAvailabilityDesc: '最多百万级Agent模拟'
      }
    },
    workflow: {
      title: '工作流序列',
      steps: [
        {
          title: '图谱构建',
          desc: '现实种子提取 & 个体与群体记忆注入 & GraphRAG构建'
        },
        {
          title: '环境搭建',
          desc: '实体关系抽取 & 人设生成 & 环境配置Agent注入仿真参数'
        },
        {
          title: '开始模拟',
          desc: '双平台并行模拟 & 自动解析预测需求 & 动态更新时序记忆'
        },
        {
          title: '报告生成',
          desc: 'ReportAgent拥有丰富的工具集与模拟后环境进行深度交互'
        },
        {
          title: '深度互动',
          desc: '与模拟世界中的任意一位进行对话 & 与ReportAgent进行对话'
        }
      ]
    },
    console: {
      upload: {
        label: '01 / 现实种子',
        formats: '支持格式: PDF, MD, TXT',
        dragTitle: '拖拽文件上传',
        dragHint: '或点击浏览文件系统',
        uploadedFiles: '已上传文件'
      },
      input: {
        label: '>_ 02 / 模拟提示词',
        placeholder: '// 用自然语言输入模拟或预测需求（例.武大若发布撤销肖某处分的公告，会引发什么舆情走向）',
        engine: '引擎: MiroFish-V1.0'
      },
      button: {
        start: '启动引擎',
        initializing: '初始化中...'
      }
    }
  },
  main: {
    viewModes: {
      graph: '图谱',
      split: '双栏',
      workbench: '工作台'
    },
    steps: [
      '图谱构建',
      '环境搭建',
      '开始模拟',
      '报告生成',
      '深度互动'
    ],
    status: {
      ready: '准备就绪',
      error: '错误',
      building: '构建图谱中',
      generating: '生成本体中',
      initializing: '初始化中'
    }
  },
  components: {
    step1: {
      title: '图谱构建',
      status: {
        initializing: '初始化中...',
        uploading: '上传和分析文档中...',
        generating: '生成本体中...',
        building: '构建知识图谱中...',
        completed: '图谱构建完成',
        failed: '图谱构建失败'
      },
      buttons: {
        nextStep: '下一步: 环境搭建'
      }
    },
    step2: {
      title: '环境搭建',
      description: '配置模拟环境和智能体人设',
      buttons: {
        startSimulation: '开始模拟',
        goBack: '返回'
      }
    },
    step3: {
      title: '开始模拟',
      description: '运行多智能体模拟',
      buttons: {
        nextStep: '下一步: 报告生成'
      }
    },
    step4: {
      title: '报告生成',
      description: '从模拟结果生成分析报告',
      buttons: {
        nextStep: '下一步: 深度互动'
      }
    },
    step5: {
      title: '深度互动',
      description: '与智能体对话，探索模拟世界',
      buttons: {
        chat: '开始对话'
      }
    },
    history: {
      title: '项目历史',
      empty: '暂无项目',
      open: '打开项目',
      delete: '删除项目'
    }
  },
  errors: {
    noFiles: '未选择文件',
    noPrompt: '请输入模拟需求',
    uploadFailed: '文件上传失败',
    networkError: '网络错误，请重试',
    unknownError: '发生未知错误'
  }
}
