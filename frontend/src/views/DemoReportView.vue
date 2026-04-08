<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const router = useRouter()

// ─── Dados estáticos da demo ──────────────────────────────────
const demo = {
  titulo: 'Relatório de Previsão: Lançamento de Plataforma de Atendimento Digital',
  confianca: 85,
  veredicto: { label: 'LANÇAR', color: '#00e5c3', icon: '🟢' },
  summary: 'A plataforma demonstrou crescimento sustentável na simulação, com validação do canal de agências white-label como principal motor de receita e conteúdo orgânico gerando maior LTV.',
  briefing: {
    decisao: 'Diversificar canais de aquisição além do white-label',
    cenario: 'Crescimento Sustentável e Expansão',
    risco: 'Dependência de agências white-label',
    tom: 'Predominantemente positivo com ressalvas sobre concentração'
  },
  cenarios: [
    { nome: 'Crescimento Sustentável', prob: 70, cor: '#00e5c3', impacto: 'Alto impacto', desc: 'A empresa capitaliza nos canais de agências e conteúdo orgânico, com melhorias no produto estabilizando o churn e a diferenciação superando a concorrência.' },
    { nome: 'Estagnação por Dependência', prob: 20, cor: '#f5a623', impacto: 'Médio impacto', desc: 'A forte dependência do canal white-label e a persistência da guerra de preços limitam o crescimento e a diversificação de aquisição.' },
    { nome: 'Crise Operacional', prob: 10, cor: '#ff5a5a', impacto: 'Alto impacto', desc: 'Instabilidade da API combinada com alto churn e intensificação da guerra de preços paralisa as vendas e afeta a reputação.' },
  ],
  insights: [
    'O canal de vendas white-label para agências é o principal motor de MRR, superando a venda direta para PMEs em eficácia.',
    'Clientes adquiridos via conteúdo orgânico demonstram um LTV significativamente maior devido à educação e expectativa calibrada.',
    'A guerra de preços iniciada por concorrentes nacionais impactou negativamente a aquisição de PMEs, mas perdeu força com a diferenciação do produto.',
    'O churn de engajamento de clientes Lifetime Deal é uma preocupação real que exige atenção contínua ao onboarding e suporte.',
    'A dependência de agências white-label, embora lucrativa, apresenta um risco estratégico que precisa ser mitigado.',
  ],
  riscos: [
    { name: 'Dependência de Agências White-label', desc: 'Alta concentração de MRR em poucas agências pode criar vulnerabilidade.', prob: 30, impacto: 'Alto', color: '#ff5a5a' },
    { name: 'Instabilidade da API do WhatsApp', desc: 'Eventos de bloqueio temporário podem paralisar novas vendas.', prob: 25, impacto: 'Alto', color: '#ff5a5a' },
    { name: 'Churn de Lifetime Deals', desc: 'Taxa de churn pode permanecer elevada se o onboarding não for otimizado.', prob: 20, impacto: 'Médio', color: '#f5a623' },
    { name: 'Guerra de Preços Persistente', desc: 'Concorrência pode intensificar guerra de preços, dificultando aquisição de PMEs.', prob: 15, impacto: 'Médio', color: '#f5a623' },
  ],
  recomendacoes: [
    { name: 'Diversificar Canais de Aquisição', desc: 'Investir na expansão de marketing de conteúdo e campanhas direcionadas a PMEs para reduzir dependência do white-label.', urgencia: 'Urgente', prazo: 'Próximos 3 meses', urgColor: '#ff5a5a' },
    { name: 'Otimizar Onboarding de Lifetime Deals', desc: 'Implementar programa de onboarding estruturado e automatizado focado na ativação nos primeiros 60 dias.', urgencia: 'Alta', prazo: 'Próximos 2 meses', urgColor: '#f5a623' },
    { name: 'Fortalecer Monitoramento de API', desc: 'Desenvolver sistema robusto de monitoramento e plano de contingência para instabilidades.', urgencia: 'Média', prazo: 'Próximos 4 meses', urgColor: '#00e5c3' },
  ],
  previsoes: [
    'Até maio de 2027, o MRR de agências white-label representará mais de 60% ± 10% do MRR total.',
    'Em agosto de 2027, a taxa de churn de Lifetime Deal reduzirá para menos de 30% ± 8% com melhorias no onboarding.',
    'Até novembro de 2027, o tráfego orgânico representará mais de 40% ± 12% dos leads qualificados.',
  ]
}
</script>

<template>
  <AppShell>
    <div class="demo-wrap">
      <!-- Banner -->
      <div class="demo-banner">
        <span>📊 RELATÓRIO DE DEMONSTRAÇÃO</span>
        <span class="demo-sub">Este é um exemplo de análise gerada pelo AUGUR. Crie seu próprio projeto para obter previsões personalizadas.</span>
        <AugurButton variant="primary" @click="router.push('/projeto/novo')" style="margin-left:auto">Criar Meu Projeto →</AugurButton>
      </div>

      <!-- Hero -->
      <section class="rpt-hero">
        <div class="hero-gauge">
          <svg viewBox="0 0 120 90" class="gauge-svg">
            <path d="M 16 75 A 52 52 0 0 1 104 75" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10" stroke-linecap="round"/>
            <path d="M 16 75 A 52 52 0 0 1 93 35" fill="none" stroke="url(#gGrad)" stroke-width="10" stroke-linecap="round"/>
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

      <!-- CTA -->
      <section class="demo-cta">
        <h3>Impressionado? Crie sua própria análise.</h3>
        <p>Em 15 minutos, o AUGUR simula o futuro do seu lançamento com 30 agentes de IA autônomos.</p>
        <AugurButton variant="primary" size="lg" @click="router.push('/projeto/novo')">Criar Meu Projeto →</AugurButton>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.demo-wrap { max-width:1100px; margin:0 auto; padding:0 20px 60px; }
.demo-banner { display:flex; align-items:center; gap:12px; padding:12px 20px; background:linear-gradient(90deg, rgba(124,111,247,0.08), rgba(0,229,195,0.06)); border:1px solid rgba(124,111,247,0.2); border-radius:12px; margin-bottom:24px; flex-wrap:wrap; font-size:13px; font-weight:700; color:#7c6ff7; }
.demo-sub { font-weight:400; color:#8888aa; font-size:12px; }
.rpt-hero { display:grid; grid-template-columns:auto 1fr; gap:24px; align-items:start; background:linear-gradient(135deg, rgba(124,111,247,0.06), rgba(0,229,195,0.04)); border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:28px; margin-bottom:24px; }
.gauge-svg { width:130px; }
.hero-veredicto { display:inline-flex; align-items:center; gap:6px; padding:6px 18px; border-radius:20px; font-size:13px; font-weight:800; letter-spacing:1px; border:2px solid; text-transform:uppercase; margin-bottom:10px; }
.hero-label { font-size:11px; font-weight:700; letter-spacing:2px; color:#00e5c3; margin-bottom:8px; }
.hero-text { font-size:14px; color:#8888aa; line-height:1.75; }
.rpt-section { background:#111118; border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:24px; margin-bottom:20px; }
.sec-header { display:flex; align-items:center; gap:10px; margin-bottom:20px; padding-bottom:14px; border-bottom:1px solid rgba(255,255,255,0.06); }
.sec-header h3 { font-size:17px; font-weight:700; color:#f0f0ff; flex:1; }
.sec-icon { font-size:20px; }
.sec-count { background:#00e5c3; color:#09090f; font-size:12px; font-weight:800; width:26px; height:26px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
.ceo-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.ceo-card { background:#16161f; border:1px solid rgba(255,255,255,0.06); border-radius:12px; padding:16px; }
.ceo-label { font-size:9px; font-weight:700; letter-spacing:1.5px; color:#555570; text-transform:uppercase; margin-bottom:8px; }
.ceo-value { font-size:14px; font-weight:600; color:#f0f0ff; line-height:1.4; }
.prob-bar { display:flex; height:28px; border-radius:14px; overflow:hidden; background:#16161f; margin-bottom:16px; }
.prob-bar div { min-width:2%; }
.cenario-cards { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
.cenario-card { background:rgba(255,255,255,0.02); border-radius:12px; padding:18px; border:1px solid rgba(255,255,255,0.06); }
.cc-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; }
.cc-header h4 { font-size:14px; font-weight:700; color:#f0f0ff; }
.cc-badge { font-size:10px; font-weight:700; }
.cenario-card p { font-size:12px; color:#8888aa; line-height:1.6; margin-bottom:8px; }
.insights-list { display:flex; flex-direction:column; gap:10px; }
.insight-item { display:flex; gap:14px; padding:14px; background:#16161f; border-radius:10px; border:1px solid rgba(255,255,255,0.06); }
.ins-num { font-size:14px; font-weight:800; color:#7c6ff7; background:rgba(124,111,247,0.1); width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.insight-item p { font-size:13px; color:#8888aa; line-height:1.6; }
.risk-cards { display:flex; flex-direction:column; gap:12px; }
.risk-card { background:#16161f; border:1px solid rgba(255,255,255,0.06); border-radius:12px; padding:18px; }
.rc-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.rc-header h4 { font-size:14px; font-weight:700; color:#f0f0ff; }
.rc-badge { font-size:10px; font-weight:700; }
.risk-card p { font-size:12px; color:#8888aa; line-height:1.6; margin-bottom:8px; }
.rc-prob { font-size:12px; color:#555570; }
.rc-prob strong { color:#f0f0ff; }
.rec-cards { display:flex; flex-direction:column; gap:12px; }
.rec-card { display:flex; gap:14px; background:#16161f; border:1px solid rgba(255,255,255,0.06); border-radius:12px; padding:18px; }
.rec-top { border:2px solid #00e5c3 !important; background:linear-gradient(135deg, rgba(0,229,195,0.06), rgba(124,111,247,0.03)) !important; position:relative; }
.rec-num { font-size:16px; font-weight:800; color:#00e5c3; background:rgba(0,229,195,0.08); width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.rec-body { flex:1; }
.rec-top-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.rec-top-row h4 { font-size:14px; font-weight:700; color:#f0f0ff; }
.rec-urg { font-size:11px; font-weight:700; }
.rec-body p { font-size:12px; color:#8888aa; line-height:1.6; }
.rec-prazo { font-size:11px; color:#555570; margin-top:8px; }
.demo-cta { text-align:center; padding:40px; background:linear-gradient(135deg, rgba(124,111,247,0.06), rgba(0,229,195,0.04)); border:1px solid rgba(255,255,255,0.06); border-radius:16px; }
.demo-cta h3 { font-size:18px; color:#f0f0ff; margin-bottom:8px; }
.demo-cta p { font-size:13px; color:#8888aa; margin-bottom:20px; line-height:1.6; }
@media (max-width:768px) { .ceo-grid { grid-template-columns:1fr 1fr; } .cenario-cards { grid-template-columns:1fr; } .rpt-hero { grid-template-columns:1fr; text-align:center; } }
</style>
