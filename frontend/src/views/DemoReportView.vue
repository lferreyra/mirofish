<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const router = useRouter()
const activeDemo = ref(0)

const demos = [
  // ─── DEMO 1: VAREJO — Loja de Móveis ──────────────────────
  {
    tag: '🪑 Varejo',
    setor: 'Varejo Local',
    titulo: 'Abertura de Loja de Móveis Planejados em Criciúma-SC',
    confianca: 58,
    veredicto: { label: 'AJUSTAR', color: '#f5a623', icon: '🟡' },
    summary: 'Criciúma comporta um novo player de móveis planejados, mas apenas se evitar competição direta em preço com as redes estabelecidas e investir em showroom experiencial de pelo menos 120m². Sem diferenciação clara, o negócio estagna em R$35k/mês — insuficiente para cobrir custos fixos.',
    briefing: {
      decisao: 'Abrir com showroom premium de 120m² no Centro ou Próspera',
      cenario: 'Crescimento lento mas sustentável (break-even M14)',
      risco: 'Loja Becker reagir com linha premium própria',
      tom: 'Cautelosamente positivo — 58% de confiança'
    },
    cenarios: [
      { nome: 'Referência em Projetos Sob Medida', prob: 30, cor: '#00e5c3', impacto: 'R$120k/mês', desc: 'Showroom vira referência. Instagram com portfólio atrai público A/B. Indicação responde por 55% dos leads após M9. Break-even no M11.' },
      { nome: 'Crescimento Lento mas Sustentável', prob: 45, cor: '#f5a623', impacto: 'R$85k/mês', desc: 'Crescimento gradual com indicações e Instagram. Break-even no M14. Becker lança linha premium básica mas sem qualidade. Disciplina financeira rigorosa necessária.' },
      { nome: 'Estagnação por Falta de Diferenciação', prob: 25, cor: '#ff5a5a', impacto: 'R$35k/mês', desc: 'Showroom pequeno ou mal localizado. Público não percebe diferença. Instagram não decola. Becker reage com promoções agressivas. Prejuízo contínuo.' },
    ],
    insights: [
      'Criciúma movimenta R$45M/ano em móveis, 62% em parcelas. Crediário é a moeda dominante.',
      'O nicho de móveis planejados premium cresce 23% ao ano na região, vs 4% do varejo geral.',
      '72% dos agentes afirmaram que sem showroom físico de qualidade, não fechariam negócio acima de R$8k.',
      'Loja Becker tem 4.200 clientes com crediário ativo — barreira alta de troca.',
      'Clientes conquistados por indicação têm ticket médio 40% maior que os de Instagram.',
      'Sazonalidade forte: janeiro e fevereiro representam queda de 35% no faturamento.',
    ],
    riscos: [
      { name: 'Reação da Loja Becker', desc: 'Líder com 4.200 crediários ativos pode lançar linha premium própria para bloquear o entrante.', prob: 45, impacto: 'Alto', color: '#ff5a5a' },
      { name: 'Showroom Insuficiente', desc: 'Espaço menor que 100m² ou localização fora do eixo central reduz conversão em 72%.', prob: 35, impacto: 'Alto', color: '#ff5a5a' },
      { name: 'Cash Flow nos Primeiros 14 Meses', desc: 'Break-even só no M14. Capital de giro de R$250k pode não ser suficiente com atrasos em projetos.', prob: 40, impacto: 'Alto', color: '#ff5a5a' },
      { name: 'Erosão por Marketplaces', desc: 'Shopee e Mercado Livre competem por preço em móveis modulados, comprimindo margem do segmento médio.', prob: 30, impacto: 'Médio', color: '#f5a623' },
    ],
    recomendacoes: [
      { name: 'Showroom Premium de 120m² no Centro', desc: 'Investir R$90-110k em espaço experiencial. Cada visita ao showroom converte a 35% vs 4% online. É a recomendação que decide sobrevivência.', urgencia: 'Urgente', prazo: 'Antes de abrir', urgColor: '#ff5a5a' },
      { name: 'Base de Indicação via WhatsApp', desc: 'Criar programa "Indique e Ganhe" com desconto progressivo. Indicação será 40-55% dos leads após M12.', urgencia: 'Alta', prazo: 'M1-3', urgColor: '#f5a623' },
      { name: 'Portfólio Instagram Profissional', desc: 'Fotógrafo profissional para cada projeto entregue. Antes/depois com métricas. Custo: R$2k/mês → ROI de 8x.', urgencia: 'Alta', prazo: 'M1-6', urgColor: '#f5a623' },
    ],
    previsoes: [
      'Até M6, captação de 25-40 contatos/mês com conversão de 12-18%. Probabilidade: 79% ±8%.',
      'Break-even entre M11-16 dependendo do cenário. Probabilidade cenário base: 71% ±7%.',
      'Faturamento estável de R$85-120k/mês a partir de M18. Probabilidade: 64% ±9%.',
      'Indicação como fonte #1 de leads após M9. Probabilidade: 82% ±6%.',
    ]
  },

  // ─── DEMO 2: SaaS — Plataforma de Atendimento ──────────────
  {
    tag: '💻 SaaS B2B',
    setor: 'SaaS B2B',
    titulo: 'Lançamento de Plataforma de Atendimento Digital para PMEs',
    confianca: 85,
    veredicto: { label: 'LANÇAR', color: '#00e5c3', icon: '🟢' },
    summary: 'A plataforma demonstrou crescimento sustentável na simulação. O canal de agências white-label é o principal motor de receita, e conteúdo orgânico gera maior LTV. Recomendação: lançar com foco em diversificação de canais.',
    briefing: {
      decisao: 'Lançar e diversificar canais além do white-label',
      cenario: 'Crescimento sustentável com expansão via agências',
      risco: 'Dependência excessiva de agências white-label',
      tom: 'Predominantemente positivo — 85% de confiança'
    },
    cenarios: [
      { nome: 'Crescimento Sustentável e Expansão', prob: 70, cor: '#00e5c3', impacto: 'MRR R$180k', desc: 'White-label + conteúdo orgânico criam base sólida. Churn estabiliza em 3.5%. Diferenciação supera guerra de preços. MRR atinge R$180k no M24.' },
      { nome: 'Estagnação por Dependência', prob: 20, cor: '#f5a623', impacto: 'MRR R$80k', desc: 'Dependência do white-label e guerra de preços limitam crescimento. MRR estagna em R$80k. Diversificação de canais não avança.' },
      { nome: 'Crise Operacional', prob: 10, cor: '#ff5a5a', impacto: 'MRR R$25k', desc: 'Instabilidade de API + alto churn + guerra de preços paralisa vendas. Reputação afetada. MRR cai para R$25k.' },
    ],
    insights: [
      'Canal white-label para agências supera venda direta para PMEs em eficácia de aquisição. CAC 60% menor.',
      'Clientes via conteúdo orgânico têm LTV 3.2x maior — educação calibra expectativa e reduz churn.',
      'Guerra de preços por concorrentes nacionais impactou aquisição de PMEs mas perdeu força com diferenciação.',
      'Churn de engajamento em clientes Lifetime Deal é 2.8x maior que assinantes mensais.',
      'NPS de 72 entre clientes white-label vs 48 entre clientes diretos — canal influencia satisfação.',
    ],
    riscos: [
      { name: 'Dependência de Agências White-label', desc: 'Alta concentração de MRR em poucas agências. Se 2 grandes saírem, impacto de 35% no MRR.', prob: 30, impacto: 'Alto', color: '#ff5a5a' },
      { name: 'Instabilidade da API do WhatsApp', desc: 'Bloqueios temporários podem paralisar novas vendas e gerar churn de 15% em 30 dias.', prob: 25, impacto: 'Alto', color: '#ff5a5a' },
      { name: 'Churn de Lifetime Deals', desc: 'Taxa de churn pode permanecer elevada se onboarding não for otimizado nos primeiros 60 dias.', prob: 20, impacto: 'Médio', color: '#f5a623' },
      { name: 'Guerra de Preços', desc: 'Concorrentes podem intensificar guerra de preços, forçando redução de pricing.', prob: 15, impacto: 'Médio', color: '#f5a623' },
    ],
    recomendacoes: [
      { name: 'Diversificar Canais de Aquisição', desc: 'Expandir marketing de conteúdo e campanhas para PMEs. Reduzir dependência do white-label de 70% para 45% do MRR.', urgencia: 'Urgente', prazo: 'Próximos 3 meses', urgColor: '#ff5a5a' },
      { name: 'Otimizar Onboarding Lifetime Deals', desc: 'Programa estruturado de ativação nos primeiros 60 dias. Sequência de 8 emails + 2 calls. Reduz churn de 40% para 18%.', urgencia: 'Alta', prazo: 'Próximos 2 meses', urgColor: '#f5a623' },
      { name: 'Monitoramento de API Robusto', desc: 'Sistema de alertas + plano de contingência + comunicação proativa para instabilidades. Tempo de resposta < 15min.', urgencia: 'Média', prazo: 'Próximos 4 meses', urgColor: '#00e5c3' },
    ],
    previsoes: [
      'Até M12, MRR de agências white-label representará 60% ±10% do MRR total.',
      'Churn de Lifetime Deal reduzirá para menos de 18% ±8% com melhorias no onboarding.',
      'Tráfego orgânico representará 40% ±12% dos leads qualificados até M18.',
      'CAC médio cairá de R$450 para R$280 ±15% com maturação dos canais orgânicos.',
    ]
  },

  // ─── DEMO 3: ALIMENTAÇÃO — Restaurante ──────────────────────
  {
    tag: '🍽️ Alimentação',
    setor: 'Alimentação',
    titulo: 'Abertura de Restaurante Japonês em Nova Friburgo-RJ',
    confianca: 62,
    veredicto: { label: 'AJUSTAR', color: '#f5a623', icon: '🟡' },
    summary: 'Nova Friburgo tem demanda reprimida por culinária japonesa de qualidade — a cidade tem 190 mil habitantes e apenas 2 restaurantes japoneses, ambos avaliados abaixo de 4.0 no Google. Porém, o custo de insumos frescos (peixe, frutos do mar) na serra fluminense é 35-45% maior que no litoral, comprimindo margem. Viável se operar com cardápio híbrido (japonês + contemporâneo) e delivery forte via iFood.',
    briefing: {
      decisao: 'Abrir com cardápio híbrido e operação delivery desde o dia 1',
      cenario: 'Crescimento moderado com delivery como motor (break-even M10)',
      risco: 'Custo de insumos frescos corroer margem abaixo de 50%',
      tom: 'Cautelosamente otimista — demanda existe mas operação é complexa'
    },
    cenarios: [
      { nome: 'Referência Gastronômica da Serra', prob: 25, cor: '#00e5c3', impacto: 'R$95k/mês', desc: 'Restaurante vira destino gastronômico. Turistas de fim de semana (Petrópolis, Teresópolis, RJ) representam 30% do faturamento. Avaliação 4.7 no Google. Break-even M8.' },
      { nome: 'Operação Estável com Delivery', prob: 50, cor: '#f5a623', impacto: 'R$55k/mês', desc: 'Delivery via iFood responde por 45% do faturamento. Salão funciona bem nos fins de semana. Margem apertada (48%) mas sustentável. Break-even M10.' },
      { nome: 'Margem Comprimida e Estagnação', prob: 25, cor: '#ff5a5a', impacto: 'R$28k/mês', desc: 'Custo de insumos frescos inviabiliza cardápio premium. Sashimi retirado do menu. Restaurante perde identidade e vira "mais um japonês genérico". Faturamento insuficiente.' },
    ],
    insights: [
      'Nova Friburgo tem apenas 2 restaurantes japoneses, ambos com avaliação abaixo de 4.0 — há espaço claro para qualidade.',
      'Custo do salmão fresco na serra é R$65-78/kg vs R$45-52/kg no litoral. Margem do sashimi cai de 65% para 42%.',
      'Delivery via iFood em Nova Friburgo cresce 28% ao ano. Taxa de comissão: 23% para restaurantes novos.',
      'Turismo de fim de semana (35.000 visitantes/mês) é oportunidade subaproveitada — nenhum japonês tem presença em guias.',
      'O cardápio híbrido (temakis + bowls contemporâneos) teve aprovação de 78% dos agentes vs 52% para cardápio tradicional puro.',
      'Fornecedor de peixe congelado de qualidade (Sushi Grade) reduz custo em 30% com perda aceitável de qualidade.',
    ],
    riscos: [
      { name: 'Custo de Insumos Frescos', desc: 'Salmão e atum frescos na serra custam 35-45% mais que no litoral. Pode inviabilizar pratos premium.', prob: 55, impacto: 'Alto', color: '#ff5a5a' },
      { name: 'Taxa iFood 23%', desc: 'Comissão do iFood corrói margem do delivery. Se delivery for 45% do faturamento, impacto direto de 10% na margem total.', prob: 40, impacto: 'Alto', color: '#ff5a5a' },
      { name: 'Sazonalidade Turística', desc: 'Janeiro-fevereiro (verão) tem queda de 40% em turismo na serra. Depender de turista é arriscado.', prob: 50, impacto: 'Médio', color: '#f5a623' },
      { name: 'Vigilância Sanitária Rigorosa', desc: 'Peixe cru exige cadeia fria impecável. Uma notificação da VISA pode fechar o restaurante por 30 dias.', prob: 20, impacto: 'Alto', color: '#ff5a5a' },
    ],
    recomendacoes: [
      { name: 'Cardápio Híbrido: Japonês + Bowls', desc: 'Oferecer temakis, bowls e pratos quentes além do sashimi. Reduz dependência de peixe fresco e amplia público. 78% de aprovação na simulação.', urgencia: 'Urgente', prazo: 'Antes de abrir', urgColor: '#ff5a5a' },
      { name: 'Fornecedor Sushi Grade Congelado', desc: 'Negociar com fornecedor de peixe congelado de qualidade. Custo 30% menor. Testar aceitação com menu degustação antes de abrir.', urgencia: 'Alta', prazo: 'M1', urgColor: '#f5a623' },
      { name: 'Delivery Próprio + iFood', desc: 'Lançar delivery próprio via WhatsApp em paralelo ao iFood. Migrar 30% dos pedidos para canal próprio até M6 — economia de 23% em comissão.', urgencia: 'Alta', prazo: 'M1-6', urgColor: '#f5a623' },
    ],
    previsoes: [
      'Faturamento de R$30-40k/mês nos primeiros 3 meses. Probabilidade: 84% ±6%.',
      'Break-even entre M8-12 dependendo da participação do delivery. Probabilidade: 68% ±8%.',
      'Avaliação Google acima de 4.5 até M6 se qualidade for consistente. Probabilidade: 72% ±10%.',
      'Delivery representará 40-50% do faturamento até M12. Probabilidade: 77% ±7%.',
    ]
  }
]

const demo = computed(() => demos[activeDemo.value])

const gaugePath = computed(() => {
  const pct = demo.value?.confianca || 50
  const angle = Math.PI - (pct / 100) * Math.PI
  const x = 60 + 52 * Math.cos(angle)
  const y = 75 - 52 * Math.sin(angle)
  const large = pct > 50 ? 1 : 0
  return `M 16 75 A 52 52 0 ${large} 1 ${x.toFixed(1)} ${y.toFixed(1)}`
})
</script>

<template>
  <AppShell>
    <div class="demo-wrap">
      <!-- Banner -->
      <div class="demo-banner">
        <span>📊 RELATÓRIOS DE DEMONSTRAÇÃO</span>
        <span class="demo-sub">Explore 3 análises reais geradas pelo AUGUR em setores diferentes.</span>
        <AugurButton variant="primary" @click="router.push('/projeto/novo')" style="margin-left:auto">Criar Meu Projeto →</AugurButton>
      </div>

      <!-- Seletor de Demo -->
      <div class="demo-tabs">
        <button v-for="(d, i) in demos" :key="i"
          :class="['demo-tab', { active: activeDemo === i }]"
          @click="activeDemo = i">
          <span class="tab-tag">{{ d.tag }}</span>
          <span class="tab-setor">{{ d.setor }}</span>
          <span class="tab-verdict" :style="{ color: d.veredicto.color }">{{ d.veredicto.icon }} {{ d.veredicto.label }}</span>
        </button>
      </div>

      <!-- Título -->
      <h1 class="demo-title">{{ demo.titulo }}</h1>

      <!-- Hero -->
      <section class="rpt-hero">
        <div class="hero-gauge">
          <svg viewBox="0 0 120 90" class="gauge-svg">
            <path d="M 16 75 A 52 52 0 0 1 104 75" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10" stroke-linecap="round"/>
            <path :d="gaugePath" fill="none" stroke="url(#gGrad)" stroke-width="10" stroke-linecap="round"/>
            <defs><linearGradient id="gGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#7c6ff7"/><stop offset="100%" stop-color="#00e5c3"/></linearGradient></defs>
            <text x="60" y="62" text-anchor="middle" fill="#f0f0ff" font-size="28" font-weight="800">{{ demo.confianca }}%</text>
            <text x="60" y="78" text-anchor="middle" fill="#8888aa" font-size="9" font-weight="600" letter-spacing="1.5">CONFIANÇA</text>
          </svg>
        </div>
        <div class="hero-content">
          <div class="hero-veredicto" :style="{background: demo.veredicto.color + '15', borderColor: demo.veredicto.color + '44', color: demo.veredicto.color}">
            {{ demo.veredicto.icon }} {{ demo.veredicto.label }}
          </div>
          <h2 class="hero-label">RESUMO EXECUTIVO</h2>
          <p class="hero-text">{{ demo.summary }}</p>
        </div>
      </section>

      <!-- CEO Briefing -->
      <section class="rpt-section">
        <div class="sec-header"><span class="sec-icon">🧭</span><h3>Briefing CEO — 1 Minuto</h3></div>
        <div class="ceo-grid">
          <div class="ceo-card"><div class="ceo-label">DECISÃO RECOMENDADA</div><div class="ceo-value">{{ demo.briefing.decisao }}</div></div>
          <div class="ceo-card"><div class="ceo-label">CENÁRIO MAIS PROVÁVEL</div><div class="ceo-value">{{ demo.briefing.cenario }}</div></div>
          <div class="ceo-card"><div class="ceo-label">RISCO CRÍTICO</div><div class="ceo-value" style="color:#ff5a5a">{{ demo.briefing.risco }}</div></div>
          <div class="ceo-card"><div class="ceo-label">SENTIMENTO</div><div class="ceo-value">{{ demo.briefing.tom }}</div></div>
        </div>
      </section>

      <!-- Cenários -->
      <section class="rpt-section">
        <div class="sec-header"><span class="sec-icon">🎯</span><h3>Cenários Futuros</h3><span class="sec-count">3</span></div>
        <div class="prob-bar"><div v-for="c in demo.cenarios" :key="c.nome" :style="{width: c.prob+'%', background: c.cor}"></div></div>
        <div class="cenario-cards">
          <div v-for="c in demo.cenarios" :key="c.nome" class="cenario-card" :style="{'border-left': '4px solid ' + c.cor}">
            <div class="cc-header"><h4>{{ c.nome }}</h4><span class="cc-badge" :style="{color: c.cor}">{{ c.impacto }}</span></div>
            <p>{{ c.desc }}</p>
            <strong :style="{color: c.cor}">{{ c.prob }}%</strong>
          </div>
        </div>
      </section>

      <!-- Insights -->
      <section class="rpt-section">
        <div class="sec-header"><span class="sec-icon">💡</span><h3>Insights Principais</h3><span class="sec-count">{{ demo.insights.length }}</span></div>
        <div class="insights-list">
          <div v-for="(ins, i) in demo.insights" :key="i" class="insight-item">
            <span class="ins-num">{{ i + 1 }}</span><p>{{ ins }}</p>
          </div>
        </div>
      </section>

      <!-- Riscos -->
      <section class="rpt-section">
        <div class="sec-header"><span class="sec-icon">⚠️</span><h3>Fatores de Risco</h3><span class="sec-count">{{ demo.riscos.length }}</span></div>
        <div class="risk-cards">
          <div v-for="r in demo.riscos" :key="r.name" class="risk-card" :style="{'border-left': '4px solid ' + r.color}">
            <div class="rc-header"><h4>{{ r.name }}</h4><span class="rc-badge" :style="{color: r.color}">{{ r.impacto }}</span></div>
            <p>{{ r.desc }}</p>
            <div class="rc-prob"><span>Probabilidade:</span> <strong>{{ r.prob }}%</strong></div>
          </div>
        </div>
      </section>

      <!-- Recomendações -->
      <section class="rpt-section">
        <div class="sec-header"><span class="sec-icon">⚡</span><h3>Recomendações Estratégicas</h3><span class="sec-count">{{ demo.recomendacoes.length }}</span></div>
        <div class="rec-cards">
          <div v-for="(r, i) in demo.recomendacoes" :key="i" class="rec-card" :class="{'rec-top': i === 0}">
            <div class="rec-num">{{ i + 1 }}</div>
            <div class="rec-body">
              <div class="rec-top-row"><h4>{{ r.name }}</h4><span class="rec-urg" :style="{color: r.urgColor}">{{ r.urgencia }}</span></div>
              <p>{{ r.desc }}</p>
              <div class="rec-prazo">🕐 {{ r.prazo }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Previsões -->
      <section class="rpt-section">
        <div class="sec-header"><span class="sec-icon">🔮</span><h3>Previsões com Intervalo de Confiança</h3><span class="sec-count">{{ demo.previsoes.length }}</span></div>
        <div class="insights-list">
          <div v-for="(p, i) in demo.previsoes" :key="i" class="insight-item">
            <span class="ins-num" style="background:rgba(0,229,195,0.1);color:#00e5c3">{{ i + 1 }}</span>
            <p>{{ p }}</p>
          </div>
        </div>
      </section>

      <!-- CTA -->
      <section class="demo-cta">
        <h3>Quer uma análise assim para o seu negócio?</h3>
        <p>Em 15 minutos, o AUGUR simula o futuro do seu lançamento com agentes de IA autônomos, dados de mercado verificados e relatório profissional.</p>
        <AugurButton variant="primary" size="lg" @click="router.push('/projeto/novo')">Criar Meu Projeto →</AugurButton>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
:deep(.app-content) {
  --bg-base: #f5f5fa; --bg-surface: #ffffff; --bg-raised: #fafafe; --bg-overlay: #f0f0f5;
  --border: #eeeef2; --border-md: #dddde5; --text-primary: #1a1a2e; --text-secondary: #444466;
  --text-muted: #8888aa; --accent: #00e5c3; --accent-dim: rgba(0,229,195,0.08);
  --accent2: #7c6ff7; --accent2-dim: rgba(124,111,247,0.08); --danger: #ff5a5a;
}

.demo-wrap { max-width:1100px; margin:0 auto; padding:0 20px 60px; }
.demo-banner { display:flex; align-items:center; gap:12px; padding:12px 20px; background:linear-gradient(90deg, rgba(124,111,247,0.08), rgba(0,229,195,0.06)); border:1px solid rgba(124,111,247,0.2); border-radius:12px; margin-bottom:20px; flex-wrap:wrap; font-size:13px; font-weight:700; color:#7c6ff7; }
.demo-sub { font-weight:400; color:#8888aa; font-size:12px; }

/* ─── Tab Selector ─── */
.demo-tabs { display:flex; gap:10px; margin-bottom:24px; }
.demo-tab { flex:1; padding:14px 16px; background:var(--bg-surface); border:2px solid var(--border); border-radius:14px; cursor:pointer; text-align:center; transition:all .25s; display:flex; flex-direction:column; gap:4px; }
.demo-tab:hover { border-color:var(--accent2); }
.demo-tab.active { border-color:var(--accent); background:linear-gradient(135deg, rgba(0,229,195,0.06), rgba(124,111,247,0.04)); box-shadow:0 2px 12px rgba(0,229,195,0.15); }
.tab-tag { font-size:16px; }
.tab-setor { font-size:11px; font-weight:700; letter-spacing:1px; color:var(--text-muted); text-transform:uppercase; }
.tab-verdict { font-size:12px; font-weight:800; }

.demo-title { font-size:22px; font-weight:800; color:var(--text-primary); margin-bottom:20px; line-height:1.3; }

/* ─── Sections ─── */
.rpt-hero { display:grid; grid-template-columns:auto 1fr; gap:24px; align-items:start; background:linear-gradient(135deg, rgba(124,111,247,0.06), rgba(0,229,195,0.04)); border:1px solid var(--border); border-radius:16px; padding:28px; margin-bottom:24px; }
.gauge-svg { width:130px; }
.gauge-svg text { fill: var(--text-primary); }
.gauge-svg text:last-child { fill: var(--text-muted); }
.hero-veredicto { display:inline-flex; align-items:center; gap:6px; padding:6px 18px; border-radius:20px; font-size:13px; font-weight:800; letter-spacing:1px; border:2px solid; text-transform:uppercase; margin-bottom:10px; }
.hero-label { font-size:11px; font-weight:700; letter-spacing:2px; color:var(--accent); margin-bottom:8px; }
.hero-text { font-size:14px; color:var(--text-secondary); line-height:1.75; }
.rpt-section { background:var(--bg-surface); border:1px solid var(--border); border-radius:16px; padding:24px; margin-bottom:20px; }
.sec-header { display:flex; align-items:center; gap:10px; margin-bottom:20px; padding-bottom:14px; border-bottom:1px solid var(--border); }
.sec-header h3 { font-size:17px; font-weight:700; color:var(--text-primary); flex:1; }
.sec-icon { font-size:20px; }
.sec-count { background:var(--accent); color:white; font-size:12px; font-weight:800; width:26px; height:26px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
.ceo-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.ceo-card { background:var(--bg-raised); border:1px solid var(--border); border-radius:12px; padding:16px; }
.ceo-label { font-size:9px; font-weight:700; letter-spacing:1.5px; color:var(--text-muted); text-transform:uppercase; margin-bottom:8px; }
.ceo-value { font-size:14px; font-weight:600; color:var(--text-primary); line-height:1.4; }
.prob-bar { display:flex; height:28px; border-radius:14px; overflow:hidden; background:var(--bg-raised); margin-bottom:16px; }
.prob-bar div { min-width:2%; }
.cenario-cards { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
.cenario-card { background:var(--bg-raised); border-radius:12px; padding:18px; border:1px solid var(--border); }
.cc-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; }
.cc-header h4 { font-size:14px; font-weight:700; color:var(--text-primary); }
.cc-badge { font-size:10px; font-weight:700; }
.cenario-card p { font-size:12px; color:var(--text-secondary); line-height:1.6; margin-bottom:8px; }
.insights-list { display:flex; flex-direction:column; gap:10px; }
.insight-item { display:flex; gap:14px; padding:14px; background:var(--bg-raised); border-radius:10px; border:1px solid var(--border); }
.ins-num { font-size:14px; font-weight:800; color:#7c6ff7; background:rgba(124,111,247,0.1); width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.insight-item p { font-size:13px; color:var(--text-secondary); line-height:1.6; }
.risk-cards { display:flex; flex-direction:column; gap:12px; }
.risk-card { background:var(--bg-raised); border:1px solid var(--border); border-radius:12px; padding:18px; }
.rc-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.rc-header h4 { font-size:14px; font-weight:700; color:var(--text-primary); }
.rc-badge { font-size:10px; font-weight:700; }
.risk-card p { font-size:12px; color:var(--text-secondary); line-height:1.6; margin-bottom:8px; }
.rc-prob { font-size:12px; color:var(--text-muted); }
.rc-prob strong { color:var(--text-primary); }
.rec-cards { display:flex; flex-direction:column; gap:12px; }
.rec-card { display:flex; gap:14px; background:var(--bg-raised); border:1px solid var(--border); border-radius:12px; padding:18px; }
.rec-top { border:2px solid var(--accent) !important; background:linear-gradient(135deg, rgba(0,229,195,0.06), rgba(124,111,247,0.03)) !important; }
.rec-num { font-size:16px; font-weight:800; color:var(--accent); background:rgba(0,229,195,0.08); width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.rec-body { flex:1; }
.rec-top-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.rec-top-row h4 { font-size:14px; font-weight:700; color:var(--text-primary); }
.rec-urg { font-size:11px; font-weight:700; }
.rec-body p { font-size:12px; color:var(--text-secondary); line-height:1.6; }
.rec-prazo { font-size:11px; color:var(--text-muted); margin-top:8px; }
.demo-cta { text-align:center; padding:40px; background:linear-gradient(135deg, rgba(124,111,247,0.06), rgba(0,229,195,0.04)); border:1px solid var(--border); border-radius:16px; }
.demo-cta h3 { font-size:18px; color:var(--text-primary); margin-bottom:8px; }
.demo-cta p { font-size:13px; color:var(--text-secondary); margin-bottom:20px; line-height:1.6; }
@media (max-width:768px) { .demo-tabs { flex-direction:column; } .ceo-grid { grid-template-columns:1fr 1fr; } .cenario-cards { grid-template-columns:1fr; } .rpt-hero { grid-template-columns:1fr; text-align:center; } }
</style>
