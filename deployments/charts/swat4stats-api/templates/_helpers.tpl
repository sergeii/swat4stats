{{- define "swat4stats.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats.podname" -}}
{{- printf "%s-%s" .Release.Name .Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats.selectorLabels" -}}
backend: {{ .Backend }}
{{ include "swat4stats.releaseLabels" . }}
{{- end }}

{{- define "swat4stats.releaseLabels" -}}
app.kubernetes.io/name: {{ include "swat4stats.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "swat4stats.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats.labels" -}}
helm.sh/chart: {{ include "swat4stats.chart" . }}
{{ include "swat4stats.releaseLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
