{{/* Name: Hemang | Enrollment number: 24bcs10209 */}}

{{- define "stacks.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "stacks.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "stacks.name" .) | trunc 63 | trimSuffix "-" -}}
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
