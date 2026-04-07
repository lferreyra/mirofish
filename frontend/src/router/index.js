import { createRouter, createWebHistory } from 'vue-router'
import DashboardView    from '../views/DashboardView.vue'
import NovoProjetoView  from '../views/NovoProjetoView.vue'
import ProjetoView      from '../views/ProjetoView.vue'
import SimulationView   from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView       from '../views/ReportView.vue'
import InteractionView  from '../views/InteractionView.vue'
import GraphView        from '../views/GraphView.vue'
import AgentesView      from '../views/AgentesView.vue'
import InfluentesView   from '../views/InfluentesView.vue'
import CompararView     from '../views/CompararView.vue'
import PublicReportView  from '../views/PublicReportView.vue'
import AgentProfileView from '../views/AgentProfileView.vue'
import PostsTimelineView from '../views/PostsTimelineView.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: DashboardView
  },
  {
    path: '/projeto/novo',
    name: 'NovoProjeto',
    component: NovoProjetoView
  },
  {
    path: '/projeto/:projectId',
    name: 'Projeto',
    component: ProjetoView,
    props: true
  },
  {
    path: '/novo',
    redirect: '/projeto/novo'
  },
  {
    path: '/simulacao/:projectId',
    name: 'Simulacao',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulacao/:simulationId/executar',
    name: 'Execucao',
    component: SimulationRunView,
    props: true
  },
  {
    // Agentes da simulacao — grid com perfis
    path: '/simulacao/:simulationId/agentes',
    name: 'Agentes',
    component: AgentesView,
    props: true
  },
  {
    // Ranking de influencia + mapa de coalizoes
    path: '/simulacao/:simulationId/influentes',
    name: 'Influentes',
    component: InfluentesView,
    props: true
  },
  {
    // Perfil completo de um agente
    path: '/simulacao/:simulationId/agente/:agentId',
    name: 'AgentProfile',
    component: AgentProfileView,
    props: true
  },
  {
    // Timeline de todos os posts
    path: '/simulacao/:simulationId/posts',
    name: 'PostsTimeline',
    component: PostsTimelineView,
    props: true
  },
  {
    path: '/relatorio/:reportId',
    name: 'Relatorio',
    component: ReportView,
    props: true
  },
  {
    // Chat com ReportAgent
    path: '/agentes/:reportId',
    name: 'ChatAgentes',
    component: InteractionView,
    props: true
  },
  {
    path: '/projeto/:projectId/grafo',
    name: 'Grafo',
    component: GraphView,
    props: true
  },
  {
    path: '/comparar',
    name: 'Comparar',
    component: CompararView
  },
  {
    // Link público do relatório (sem sidebar, sem auth)
    path: '/r/:token',
    name: 'PublicReport',
    component: PublicReportView,
    props: true,
    meta: { public: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})
