export const shortTime = (ts) => {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ts.slice(11, 19) || ''
  }
}

export const actionTypeClass = (type) => {
  if (!type) return ''
  const t = type.toLowerCase()
  if (t.includes('confront') || t.includes('oppos')) return 'type-hostile'
  if (t.includes('support') || t.includes('coalition')) return 'type-support'
  if (t.includes('nothing') || t.includes('idle') || t.includes('react_privately')) return 'type-passive'
  return 'type-neutral'
}

export const initials = (name) => {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

export const nodeColor = (actionType, ACTION_COLORS) => {
  if (!actionType) return '#E0E0E0'
  const upper = actionType.toUpperCase()
  for (const [key, color] of Object.entries(ACTION_COLORS)) {
    if (upper.includes(key)) return color
  }
  return '#E0E0E0'
}

export const buildRequirement = (form, agentCounts, RELATIONAL_TYPE_LABELS) => {
  const parts = []
  if (form.decisionMakerName) {
    parts.push(`Decision maker: ${form.decisionMakerName}` +
      (form.decisionMakerRole ? ` — ${form.decisionMakerRole}` : '') +
      (form.decisionMakerCompany ? ` at ${form.decisionMakerCompany}` : ''))
  }
  parts.push(`Decision: ${form.decisionText}`)
  parts.push(`Relational network: ${form.relationalTypes.join(', ')}`)
  parts.push(`Temporal horizon: ${form.horizonDays} days`)
  if (form.questionsToMeasure) parts.push(`Questions to measure: ${form.questionsToMeasure}`)
  const agentDistrib = form.relationalTypes
    .map(t => `${RELATIONAL_TYPE_LABELS[t]} × ${agentCounts[t] || 10}`)
    .join(', ')
  parts.push(`Agent distribution: ${agentDistrib}`)
  return parts.join('\n')
}

export const parseImportedConfig = (text, form, agentCounts, RELATIONAL_TYPES, RELATIONAL_TYPE_LABELS) => {
  let configText = text
  const configMatch = text.match(/#CONFIG\n([\s\S]*?)\n#END_CONFIG/)
  if (configMatch) configText = configMatch[1]

  const labelToKey = {}
  for (const [key, label] of Object.entries(RELATIONAL_TYPE_LABELS)) {
    labelToKey[label.toLowerCase()] = key
  }

  for (const line of configText.split('\n')) {
    try {
      if (line.startsWith('Décideur :')) {
        const val = line.replace('Décideur :', '').trim()
        const [nameAndRole, company] = val.split(' at ')
        const [name, role] = (nameAndRole || '').split(' — ')
        if (name) form.decisionMakerName = name.trim()
        if (role) form.decisionMakerRole = role.trim()
        if (company) form.decisionMakerCompany = company.trim()
      } else if (line.startsWith('Décision :')) {
        form.decisionText = line.replace('Décision :', '').trim()
      } else if (line.startsWith('Réseau simulé :')) {
        const types = line.replace('Réseau simulé :', '').trim()
          .split(', ').map(s => s.trim()).filter(t => RELATIONAL_TYPES.includes(t))
        if (types.length) form.relationalTypes = types
      } else if (line.startsWith('Horizon temporel :')) {
        const days = parseInt(line.replace('Horizon temporel :', '').trim(), 10)
        if (!isNaN(days)) form.horizonDays = days
      } else if (line.startsWith('Questions to measure :')) {
        form.questionsToMeasure = line.replace('Questions to measure :', '').trim()
      } else if (line.startsWith('Agent distribution:')) {
        const entries = line.replace('Agent distribution:', '').trim().split(',')
        for (const entry of entries) {
          const parts = entry.trim().split(' × ')
          if (parts.length !== 2) continue
          const key = labelToKey[parts[0].trim().toLowerCase()]
          const count = parseInt(parts[1].trim(), 10)
          if (key && !isNaN(count)) agentCounts[key] = count
        }
      }
    } catch { /* ligne ignorée */ }
  }
}

export const exportReportMarkdown = (reportResult, simId) => {
  if (!reportResult) return

  let md = reportResult.markdown_content
  if (!md) {
    const title = reportResult.outline?.title || 'Private Impact Report'
    const summary = reportResult.outline?.summary || ''
    const sections = reportResult.outline?.sections || []
    md = `# ${title}\n\n`
    if (summary) md += `> ${summary}\n\n`
    sections.forEach((s, idx) => {
      const num = String(idx + 1).padStart(2, '0')
      md += `## ${num} — ${s.title || 'Section ' + num}\n\n`
      md += `${s.content || ''}\n\n`
    })
  }

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `private-impact-report-${simId || 'report'}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
