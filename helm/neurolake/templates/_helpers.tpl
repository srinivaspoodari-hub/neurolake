{{/*
Expand the name of the chart.
*/}}
{{- define "neurolake.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "neurolake.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "neurolake.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "neurolake.labels" -}}
helm.sh/chart: {{ include "neurolake.chart" . }}
{{ include "neurolake.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "neurolake.selectorLabels" -}}
app.kubernetes.io/name: {{ include "neurolake.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API labels
*/}}
{{- define "neurolake.api.labels" -}}
{{ include "neurolake.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Frontend labels
*/}}
{{- define "neurolake.frontend.labels" -}}
{{ include "neurolake.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "neurolake.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "neurolake.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database URL
*/}}
{{- define "neurolake.databaseURL" -}}
postgresql://{{ .Values.postgresql.auth.username }}:$(DB_PASSWORD)@{{ include "neurolake.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "neurolake.redisURL" -}}
redis://{{ include "neurolake.fullname" . }}-redis-master:6379/0
{{- end }}
