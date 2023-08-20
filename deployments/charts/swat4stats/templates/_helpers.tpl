{{- define "swat4stats-core.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats-core.podname" -}}
{{- printf "%s-%s" .Release.Name .Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats-core.selectorLabels" -}}
backend: {{ .Backend }}
{{ include "swat4stats-core.releaseLabels" . }}
{{- end }}

{{- define "swat4stats-core.releaseLabels" -}}
app.kubernetes.io/name: {{ include "swat4stats-core.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "swat4stats-core.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats-core.labels" -}}
helm.sh/chart: {{ include "swat4stats-core.chart" . }}
{{ include "swat4stats-core.releaseLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
