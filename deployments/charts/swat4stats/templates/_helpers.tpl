{{- define "swat4stats.fullname" -}}
{{- $context := required "context is required" .context -}}
{{- $context.Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats.componentName" -}}
{{- $componentName := required "name is required" .name -}}
{{- $context := required "context is required" .context -}}
{{- printf "%s-%s" $context.Release.Name $componentName | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats.chart" -}}
{{- $context := required "context is required" .context -}}
{{- printf "%s-%s" $context.Chart.Name $context.Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "swat4stats.commonLabels" -}}
{{- $context := required "context is required" .context -}}
app.kubernetes.io/name: {{ include "swat4stats.fullname" . }}
app.kubernetes.io/instance: {{ $context.Release.Name }}
{{- end }}

{{- define "swat4stats.componentLabels" -}}
{{- $componentName := required "componentName is required" .componentName -}}
app.kubernetes.io/component: {{ $componentName }}
{{- end }}

{{- define "swat4stats.labels" -}}
{{- $context := required "context is required" .context -}}
helm.sh/chart: {{ include "swat4stats.chart" . }}
{{ include "swat4stats.commonLabels" . }}
app.kubernetes.io/version: {{ $context.Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ $context.Release.Service }}
{{- end }}

{{- define "swat4stats.selectorLabels" -}}
{{ include "swat4stats.commonLabels" . }}
{{ include "swat4stats.componentLabels" . }}
{{- end }}

{{- define "swat4stats.deploymentLabels" -}}
{{- $componentName := required "componentName is required" .componentName -}}
{{- $context := required "context is required" .context -}}
{{ include "swat4stats.labels" . }}
{{ include "swat4stats.componentLabels" . }}
{{- end }}
