{{- define "swat4stats-api.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats-api.podname" -}}
{{- printf "%s-%s" .Release.Name .Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats-api.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats-api.labels" -}}
helm.sh/chart: {{ include "swat4stats-api.chart" . }}
{{ include "swat4stats-api.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "swat4stats-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "swat4stats-api.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
