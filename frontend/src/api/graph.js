import service, { requestWithRetry } from './index'

/**
 * Genera ontologia (caricamento documenti e requisiti di simulazione)
 * @param {Object} data - Contiene files, simulation_requirement, project_name ecc.
 * @returns {Promise}
 */
export function generateOntology(formData) {
  return requestWithRetry(() => 
    service({
      url: '/api/graph/ontology/generate',
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  )
}

/**
 * Costruisci grafo
 * @param {Object} data - Contiene project_id, graph_name ecc.
 * @returns {Promise}
 */
export function buildGraph(data) {
  return requestWithRetry(() =>
    service({
      url: '/api/graph/build',
      method: 'post',
      data
    })
  )
}

/**
 * Interroga stato attività
 * @param {String} taskId - ID attività
 * @returns {Promise}
 */
export function getTaskStatus(taskId) {
  return service({
    url: `/api/graph/task/${taskId}`,
    method: 'get'
  })
}

/**
 * Ottieni dati del grafo
 * @param {String} graphId - ID grafo
 * @returns {Promise}
 */
export function getGraphData(graphId) {
  return service({
    url: `/api/graph/data/${graphId}`,
    method: 'get'
  })
}

/**
 * Ottieni informazioni progetto
 * @param {String} projectId - ID progetto
 * @returns {Promise}
 */
export function getProject(projectId) {
  return service({
    url: `/api/graph/project/${projectId}`,
    method: 'get'
  })
}
