{{- define "swat4tracker.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4tracker.podname" -}}
{{- printf "%s-%s" .Release.Name .Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4tracker.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4tracker.labels" -}}
helm.sh/chart: {{ include "swat4tracker.chart" . }}
{{ include "swat4tracker.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "swat4tracker.selectorLabels" -}}
app.kubernetes.io/name: {{ include "swat4tracker.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
