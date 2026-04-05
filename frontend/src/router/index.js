import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import NewSimulationView from '../views/NewSimulationView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: DashboardView },
  { path: '/novo', name: 'NovaSimulacao', component: NewSimulationView },
  { path: '/simulacao/:projectId', name: 'Simulacao', component: SimulationView, props: true },
  { path: '/simulacao/:simulationId/executar', name: 'Execucao', component: SimulationRunView, props: true },
  { path: '/relatorio/:reportId', name: 'Relatorio', component: ReportView, props: true },
  { path: '/agentes/:reportId', name: 'Agentes', component: InteractionView, props: true }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
