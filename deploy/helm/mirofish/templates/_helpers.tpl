{{/* Name + fullname helpers — stable pattern used across deployment templates. */}}
{{- define "mirofish.name" -}}
{{- default "mirofish" .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "mirofish.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "mirofish.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "mirofish.labels" -}}
app.kubernetes.io/name: {{ include "mirofish.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "mirofish.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mirofish.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
