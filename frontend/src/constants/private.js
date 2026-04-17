export const RELATIONAL_TYPES = [
  'ouvrier_production', 'technicien', 'commercial',
  'manager', 'codir', 'client_externe', 'partenaire', 'concurrent',
]

export const RELATIONAL_TYPE_LABELS = {
  ouvrier_production: 'Ouvrier / Production',
  technicien: 'Technicien',
  commercial: 'Commercial',
  manager: 'Manager',
  codir: 'CODIR',
  client_externe: 'Client externe',
  partenaire: 'Partenaire',
  concurrent: 'Concurrent',
}

export const HORIZON_OPTIONS = [
  { days: 3, label: '3 jours (72h)' },
  { days: 7, label: '7 jours' },
  { days: 30, label: '30 jours' },
  { days: 180, label: '6 mois (180 jours)' },
]

export const ACTION_COLORS = {
  CONFRONT: '#F44336',
  COALITION_BUILD: '#FF9800',
  VOCAL_SUPPORT: '#4CAF50',
  SILENT_LEAVE: '#616161',
  REACT_PRIVATELY: '#E0E0E0',
  DO_NOTHING: '#E0E0E0',
}

export const STEP_NAMES = ['Requirement', 'Prepare', 'Run', 'Report', 'Interact']
