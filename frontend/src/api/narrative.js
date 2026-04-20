import service, { requestWithRetry } from './index'

/**
 * Get the full generated story for a simulation.
 * @param {string} simId
 */
export const getFullStory = (simId) => {
  return service.get(`/api/narrative/story/${simId}`)
}

/**
 * Get a single round's story beat.
 * @param {string} simId
 * @param {number} roundNum
 */
export const getRoundStory = (simId, roundNum) => {
  return service.get(`/api/narrative/story/${simId}/round/${roundNum}`)
}

/**
 * Translate a round on demand — generates prose via LLM and stores the beat.
 * @param {Object} data - { sim_id, round, platform?, tone? }
 */
export const translateRound = (data) => {
  return requestWithRetry(() => service.post('/api/narrative/translate', data), 3, 2000)
}

/**
 * Get extended character roster with emotional state.
 * @param {string} simId
 */
export const getCharacters = (simId) => {
  return service.get(`/api/narrative/characters/${simId}`)
}

/**
 * Bootstrap narrative character profiles from existing OASIS profiles.
 * @param {string} simId
 */
export const initCharacters = (simId) => {
  return requestWithRetry(() => service.post(`/api/narrative/characters/${simId}/init`), 3, 1000)
}
