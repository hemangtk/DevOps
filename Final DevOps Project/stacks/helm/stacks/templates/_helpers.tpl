{{/* Name: Hemang | Enrollment number: 24bcs10209 */}}

{{- define "stacks.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Release name and chart name are both "stacks" by default, so a plain
     "<release>-<chart>" would render "stacks-stacks-backend". Collapse the
     two when the release name already contains the chart name. */}}
{{- define "stacks.fullname" -}}
{{- $name := include "stacks.name" . -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "stacks.labels" -}}
app.kubernetes.io/name: {{ include "stacks.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "stacks.backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "stacks.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: backend
{{- end -}}

{{- define "stacks.frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "stacks.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: frontend
{{- end -}}

{{- define "stacks.postgres.selectorLabels" -}}
app.kubernetes.io/name: {{ include "stacks.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: postgres
{{- end -}}
