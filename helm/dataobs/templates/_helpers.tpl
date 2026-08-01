{{- define "dataobs.name" -}}{{ default .Chart.Name .Values.global.nameOverride | trunc 63 | trimSuffix "-" }}{{- end }}
{{- define "dataobs.fullname" -}}{{ printf "%s-%s" .Release.Name (include "dataobs.name" .) | trunc 63 | trimSuffix "-" }}{{- end }}
{{- define "dataobs.labels" -}}
app.kubernetes.io/name: {{ include "dataobs.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}
{{- define "dataobs.selector" -}}
app.kubernetes.io/name: {{ include "dataobs.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}
{{- define "dataobs.image" -}}{{- if .image.digest -}}{{ printf "%s/%s@%s" .root.Values.global.imageRegistry .image.repository .image.digest }}{{- else -}}{{ printf "%s/%s:%s" .root.Values.global.imageRegistry .image.repository .image.tag }}{{- end -}}{{- end }}
{{- define "dataobs.commonEnv" -}}
- name: DATAOBS_ENVIRONMENT
  value: {{ .Values.global.environment | quote }}
- name: DATAOBS_TENANT_MODE
  value: {{ .Values.global.tenantMode | quote }}
- name: ELASTICSEARCH_URL
  value: {{ .Values.external.elasticsearch.url | quote }}
- name: ELASTICSEARCH_USERNAME
  valueFrom: {secretKeyRef: {name: {{ .Values.external.elasticsearch.secretName | quote }}, key: {{ .Values.external.elasticsearch.usernameKey | quote }}}}
- name: ELASTICSEARCH_PASSWORD
  valueFrom: {secretKeyRef: {name: {{ .Values.external.elasticsearch.secretName | quote }}, key: {{ .Values.external.elasticsearch.passwordKey | quote }}}}
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: {{ ternary (printf "http://%s-otel-collector:4317" (include "dataobs.fullname" .)) .Values.telemetry.endpoint (eq .Values.telemetry.mode "bundled") | quote }}
- name: OTEL_SDK_DISABLED
  value: {{ not .Values.telemetry.enabled | quote }}
- name: OTEL_EXPORTER_OTLP_PROTOCOL
  value: {{ .Values.telemetry.protocol | quote }}
- name: OTEL_EXPORTER_OTLP_TIMEOUT_MS
  value: {{ .Values.telemetry.exportTimeoutMs | quote }}
- name: DATAOBS_OTEL_QUEUE_SIZE
  value: {{ .Values.telemetry.queueSize | quote }}
- name: DATAOBS_OTEL_BATCH_SIZE
  value: {{ .Values.telemetry.batchSize | quote }}
- name: OTEL_TRACES_SAMPLER_ARG
  value: {{ .Values.telemetry.traceSampleRatio | quote }}
- name: DATAOBS_RELEASE_SHA
  value: {{ .Values.telemetry.releaseSha | quote }}
- name: DATAOBS_CHART_VERSION
  value: {{ .Chart.Version | quote }}
{{- end }}
