import service, { requestWithRetry } from './index'

const DEFAULT_ONTOLOGY_HTTP_TIMEOUT_MS = 960000

const resolveOntologyHttpTimeoutMs = () => {
  const configured = Number(import.meta.env.VITE_ONTOLOGY_HTTP_TIMEOUT_MS)
  return Number.isFinite(configured) && configured > 0
    ? configured
    : DEFAULT_ONTOLOGY_HTTP_TIMEOUT_MS
}

const toFriendlyMinutes = (timeoutMs) => {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) return 'several'
  return Math.max(1, Math.round(timeoutMs / 60000))
}

export function normalizeOntologyRequestError(error) {
  const timeoutMs = resolveOntologyHttpTimeoutMs()
  const responseData = error?.response?.data || {}
  const failureCategory = responseData.failure_category
  const backendMessage = responseData.error || error?.message || 'Ontology generation failed'
  const model = responseData.model
  const requestLabel = responseData.request_label
  const status = error?.response?.status

  let message = backendMessage

  if (error?.code === 'ECONNABORTED' && String(error?.message || '').includes('timeout')) {
    message = `Ontology generation timed out after ${toFriendlyMinutes(timeoutMs)} minutes. The upstream model may be slow or temporarily unstable.`
  } else if (failureCategory === 'invalid_json') {
    message = 'Ontology generation failed because the model returned invalid JSON.'
  } else if (failureCategory === 'empty_response' || failureCategory === 'llm_response_error') {
    message = 'Ontology generation failed because the model returned an unusable response.'
  } else if (failureCategory === 'provider_unavailable' || status >= 500) {
    message = 'Ontology generation failed because the upstream LLM provider returned a temporary server error.'
  }

  const normalized = new Error(message)
  normalized.name = 'OntologyRequestError'
  normalized.cause = error
  normalized.failureCategory = failureCategory || null
  normalized.model = model || null
  normalized.requestLabel = requestLabel || null
  normalized.status = status || null
  normalized.backendMessage = backendMessage
  return normalized
}

/**
 * 生成本体（上传文档和模拟需求）
 * @param {Object} data - 包含files, simulation_requirement, project_name等
 * @returns {Promise}
 */
export function generateOntology(formData) {
  return requestWithRetry(
    async () => {
      try {
        return await service({
          url: '/api/graph/ontology/generate',
          method: 'post',
          data: formData,
          timeout: resolveOntologyHttpTimeoutMs(),
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
      } catch (error) {
        throw normalizeOntologyRequestError(error)
      }
    },
    1
  )
}

/**
 * 构建图谱
 * @param {Object} data - 包含project_id, graph_name等
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
 * 查询任务状态
 * @param {String} taskId - 任务ID
 * @returns {Promise}
 */
export function getTaskStatus(taskId) {
  return service({
    url: `/api/graph/task/${taskId}`,
    method: 'get'
  })
}

/**
 * 获取图谱数据
 * @param {String} graphId - 图谱ID
 * @returns {Promise}
 */
export function getGraphData(graphId) {
  return service({
    url: `/api/graph/data/${graphId}`,
    method: 'get'
  })
}

/**
 * 获取项目信息
 * @param {String} projectId - 项目ID
 * @returns {Promise}
 */
export function getProject(projectId) {
  return service({
    url: `/api/graph/project/${projectId}`,
    method: 'get'
  })
}
