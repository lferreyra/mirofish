import { createI18n } from 'vue-i18n'

const messages = {
  'pt-BR': {
    nav: {
      dashboard: 'Dashboard',
      newSimulation: 'Nova Simulação',
      running: 'Em Execução',
      reports: 'Relatórios',
      agents: 'Entrevistar Agentes',
      settings: 'Configurações'
    },
    dashboard: {
      title: 'Dashboard',
      recentSimulations: 'Simulações Recentes',
      recentSub: 'Seus últimos projetos de previsão',
      agentActivity: 'Atividade dos Agentes',
      activitySub: 'Volume de interações por dia',
      avgSentiment: 'Sentimento médio — última semana',
      newSimulation: '+ Nova Simulação',
      export: 'Exportar',
      noSimulations: 'Nenhuma simulação ainda',
      noSimSub: 'Crie sua primeira simulação para começar'
    },
    metrics: {
      simulations: 'Simulações',
      totalAgents: 'Agentes Totais',
      avgAccuracy: 'Precisão Média',
      reports: 'Relatórios'
    },
    status: {
      completed: 'Concluído',
      running: 'Em execução',
      draft: 'Rascunho',
      failed: 'Falhou',
      preparing: 'Preparando',
      ready: 'Pronto',
      paused: 'Pausado'
    },
    wizard: {
      title: 'Nova Simulação',
      step1: 'Documento',
      step2: 'Grafo',
      step3: 'Parâmetros',
      step4: 'Agentes',
      step5: 'Executar',
      cancel: 'Cancelar',
      back: 'Voltar',
      next: 'Próximo',
      save: 'Salvar rascunho',
      start: 'Iniciar Simulação'
    },
    upload: {
      title: 'Carregue o documento semente',
      sub: 'O material base para a simulação — notícia, relatório, comunicado, análise',
      drop: 'Arraste e solte ou clique para selecionar',
      formats: 'Formatos aceitos: PDF, MD, TXT',
      uploaded: 'Arquivo carregado',
      change: 'Trocar arquivo'
    },
    params: {
      title: 'Configurar Simulação',
      sub: 'Defina os parâmetros da sua previsão de opinião pública',
      projectName: 'Nome do projeto',
      projectNamePlaceholder: 'ex: Lançamento produto X — Campanha Q2',
      objective: 'Objetivo da simulação — descreva o que quer prever',
      objectivePlaceholder: 'ex: Como o público vai reagir ao anúncio de reajuste de 15% nos preços?',
      agents: 'Agentes',
      rounds: 'Rodadas',
      hours: 'Horas simuladas',
      platforms: 'Plataformas de simulação',
      twitterDesc: 'Posts, reposts, follows',
      redditDesc: 'Posts, comentários, upvotes'
    },
    run: {
      title: 'Execução ao vivo',
      round: 'Rodada',
      of: 'de',
      progress: 'concluído',
      postsCreated: 'Posts criados',
      activeAgents: 'Agentes ativos',
      dominantTone: 'Tom dominante',
      twitterLive: 'Twitter — Ao vivo',
      redditLive: 'Reddit — Ao vivo',
      roundTimeline: 'Timeline de rodadas — sentimento acumulado',
      topicsTrending: 'Tópicos em alta',
      topAgents: 'Agentes mais influentes',
      interactions: 'interações',
      pause: 'Pausar',
      stop: 'Encerrar',
      viewReport: 'Ver Relatório'
    },
    sentiment: {
      label: 'Sentimento',
      positive: 'Positivo',
      neutral: 'Neutro',
      negative: 'Negativo',
      general: 'Sentimento geral',
      twitter: 'Sentimento — Twitter',
      reddit: 'Sentimento — Reddit'
    },
    report: {
      title: 'Relatório',
      executiveSummary: 'Sumário Executivo',
      generatedBy: 'Gerado pelo ReportAgent',
      mainPrediction: 'Predição principal',
      detailedInsights: 'Insights detalhados',
      confidence: 'Confiança',
      basedOn: 'Baseado em',
      agentInteractions: 'interações de agentes',
      metrics: 'Principais métricas',
      agentsReached: 'Agentes alcançados',
      postsGenerated: 'Posts gerados',
      purchaseIntent: 'Intenção de compra',
      viralProbability: 'Probabilidade de viral',
      emergingKeywords: 'Palavras-chave emergentes',
      exportPdf: 'Exportar PDF',
      interviewAgents: 'Entrevistar Agentes',
      tag: {
        opportunity: 'Oportunidade',
        risk: 'Risco',
        observation: 'Observação',
        neutral: 'Neutro'
      }
    },
    interaction: {
      title: 'Entrevistar Agentes',
      selectAgent: 'Agente',
      interviewAll: 'Entrevistar todos',
      allAgents: 'Todos os agentes',
      influence: 'Influência',
      sendMessage: 'Enviar pergunta ao agente...',
      send: 'Enviar',
      groupQuestion: 'Pergunta para todos os agentes ao mesmo tempo...',
      sendToAll: 'Enviar para todos os agentes',
      roundLabel: 'rodada',
      you: 'Você'
    },
    errors: {
      uploadFailed: 'Falha no upload. Tente novamente.',
      simulationFailed: 'Erro ao criar simulação.',
      networkError: 'Erro de conexão. Verifique sua rede.',
      notFound: 'Recurso não encontrado.',
      generic: 'Algo deu errado. Tente novamente.'
    },
    general: {
      loading: 'Carregando...',
      save: 'Salvar',
      cancel: 'Cancelar',
      confirm: 'Confirmar',
      delete: 'Excluir',
      edit: 'Editar',
      view: 'Visualizar',
      close: 'Fechar',
      yes: 'Sim',
      no: 'Não',
      back: 'Voltar',
      next: 'Próximo',
      finish: 'Concluir',
      agents: 'agentes',
      rounds: 'rodadas',
      hours: 'horas',
      now: 'agora',
      min: 'min',
      ago: 'atrás',
      byItcast: 'by itcast',
      productName: 'AUGUR'
    }
  }
}

export default createI18n({
  legacy: false,
  locale: 'pt-BR',
  fallbackLocale: 'pt-BR',
  messages
})
