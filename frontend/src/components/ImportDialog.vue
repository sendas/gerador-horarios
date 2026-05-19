<template>
  <q-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" persistent>
    <q-card style="min-width: 500px; max-width: 700px; width: 100%">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ title }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section>
        <q-tabs v-model="tab" dense align="left">
          <q-tab name="file" icon="upload_file" label="Ficheiro" />
          <q-tab v-if="entityType" name="image" icon="image" label="Imagem" />
        </q-tabs>

        <q-separator />

        <q-tab-panels v-model="tab" animated>
          <!-- File tab -->
          <q-tab-panel name="file" class="q-pa-none q-pt-md">
            <q-banner v-if="formatHint" dense rounded :class="$q.dark.isActive ? 'bg-blue-9' : 'bg-blue-1 text-blue-10'" class="q-mb-md">
              <template #avatar><q-icon name="info" color="blue-7" /></template>
              <div class="text-weight-medium q-mb-xs">Formato esperado:</div>
              <div class="text-caption">Colunas: <code>{{ formatHint.columns }}</code></div>
              <div v-if="formatHint.notes" class="text-caption q-mt-xs text-grey-7">{{ formatHint.notes }}</div>
            </q-banner>
            <div class="q-mb-md text-caption text-grey-7">
              Formatos suportados: CSV (.csv) e Excel (.xlsx)
            </div>

            <q-file
              v-model="selectedFile"
              label="Selecionar ficheiro"
              accept=".csv,.xlsx,.xls"
              outlined
              dense
              class="q-mb-md"
            >
              <template #prepend>
                <q-icon name="attach_file" />
              </template>
            </q-file>

            <div v-if="missingParams" class="q-mb-md">
              <q-banner dense class="bg-warning text-white rounded-borders">
                <template #avatar><q-icon name="warning" /></template>
                Parâmetros obrigatórios em falta. Selecione os filtros necessários antes de importar.
              </q-banner>
            </div>

            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn
                color="primary"
                icon="upload"
                label="Importar"
                :loading="uploading"
                :disable="!selectedFile || missingParams"
                @click="doFileUpload"
              />
            </div>

            <div v-if="result" class="q-mt-md">
              <q-banner :class="result.errors?.length ? 'bg-warning' : 'bg-positive'" class="text-white rounded-borders">
                <template #avatar><q-icon :name="result.errors?.length ? 'warning' : 'check_circle'" /></template>
                <div>Criados: <strong>{{ result.created }}</strong> &nbsp; Ignorados: <strong>{{ result.skipped }}</strong></div>
                <div v-if="result.errors?.length" class="q-mt-xs">
                  <div v-for="(err, i) in result.errors" :key="i" class="text-caption">{{ err }}</div>
                </div>
              </q-banner>
            </div>
          </q-tab-panel>

          <!-- Image tab -->
          <q-tab-panel v-if="entityType" name="image" class="q-pa-none q-pt-md">
            <div class="q-mb-md text-caption text-grey-7">
              Carregue uma imagem (lista, tabela, etc.) e a IA extrairá os dados automaticamente.
            </div>

            <q-file
              v-model="selectedImage"
              label="Selecionar imagem"
              accept="image/jpeg,image/png,image/webp,image/gif"
              outlined
              dense
              class="q-mb-md"
            >
              <template #prepend>
                <q-icon name="image" />
              </template>
            </q-file>

            <div class="row justify-end q-gutter-sm q-mb-md">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn
                color="secondary"
                icon="auto_awesome"
                label="Extrair dados"
                :loading="extracting"
                :disable="!selectedImage"
                @click="doExtract"
              />
            </div>

            <div v-if="extractedData !== null" class="q-mt-md">
              <div class="text-subtitle2 q-mb-sm">Dados extraídos ({{ extractedData.length }} registos):</div>
              <q-scroll-area style="height: 200px" class="q-mb-md">
                <pre class="text-caption q-pa-sm rounded-borders" :class="$q.dark.isActive ? 'bg-grey-9' : 'bg-grey-2'" style="white-space: pre-wrap; word-break: break-all;">{{ JSON.stringify(extractedData, null, 2) }}</pre>
              </q-scroll-area>

              <div v-if="missingParams" class="q-mb-md">
                <q-banner dense class="bg-warning text-white rounded-borders">
                  <template #avatar><q-icon name="warning" /></template>
                  Parâmetros obrigatórios em falta. Selecione os filtros necessários antes de confirmar.
                </q-banner>
              </div>

              <div class="row justify-end q-gutter-sm">
                <q-btn
                  color="primary"
                  icon="check"
                  label="Confirmar importação"
                  :loading="uploading"
                  :disable="missingParams"
                  @click="doConfirmImport"
                />
              </div>
            </div>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

const FORMAT_HINTS: Record<string, { columns: string; notes?: string }> = {
  teachers: {
    columns: 'nome, email (opcional), max_aulas_dia (opcional)',
    notes: 'max_aulas_dia: máximo de aulas por dia (padrão: 5)',
  },
  classes: {
    columns: 'nome, ano, escola_id (opcional), num_alunos (opcional)',
    notes: 'ano: nível de escolaridade (ex: 5, 6, 7)',
  },
  rooms: {
    columns: 'nome, capacidade (opcional), tipo (opcional)',
    notes: 'tipo: sala, laboratório, ginásio, etc.',
  },
  subjects: {
    columns: 'nome, cor (opcional), semestral (opcional)',
    notes: 'cor: código hex (ex: #3498db); semestral: sim/não',
  },
  curriculum: {
    columns: 'ano, turma, disciplina, horas_semana, professor (opcional), articulado (opcional)',
    notes: 'articulado: sim/não — indica se a disciplina é articulada com outra',
  },
}

const props = withDefaults(defineProps<{
  modelValue: boolean
  title: string
  endpoint: string
  extraParams?: Record<string, string | number | null | undefined>
  entityType?: string
}>(), {
  extraParams: () => ({}),
  entityType: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'done'): void
}>()

const $q = useQuasar()

const tab = ref('file')
const selectedFile = ref<File | null>(null)
const selectedImage = ref<File | null>(null)
const uploading = ref(false)
const extracting = ref(false)
const result = ref<{ created: number; skipped: number; errors: string[] } | null>(null)
const extractedData = ref<Record<string, unknown>[] | null>(null)

const formatHint = computed(() => props.entityType ? (FORMAT_HINTS[props.entityType] ?? null) : null)

const missingParams = computed(() => {
  if (!props.extraParams) return false
  return Object.values(props.extraParams).some((v) => v === null || v === undefined || v === 0 || v === '')
})

async function doFileUpload() {
  if (!selectedFile.value) return
  result.value = null
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    if (props.extraParams) {
      for (const [key, val] of Object.entries(props.extraParams)) {
        if (val !== null && val !== undefined) {
          formData.append(key, String(val))
        }
      }
    }
    const { data } = await api.post(props.endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = data
    $q.notify({ type: 'positive', message: `Importação concluída: ${data.created} criados, ${data.skipped} ignorados` })
    if (data.created > 0) emit('done')
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    $q.notify({ type: 'negative', message: error.response?.data?.detail ?? 'Erro ao importar ficheiro' })
  } finally {
    uploading.value = false
  }
}

async function doExtract() {
  if (!selectedImage.value || !props.entityType) return
  extractedData.value = null
  extracting.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedImage.value)
    formData.append('entity_type', props.entityType)
    const { data } = await api.post('/imports/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    extractedData.value = data.data as Record<string, unknown>[]
    $q.notify({ type: 'positive', message: `Extraídos ${data.data.length} registos` })
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    $q.notify({ type: 'negative', message: error.response?.data?.detail ?? 'Erro ao extrair dados da imagem' })
  } finally {
    extracting.value = false
  }
}

async function doConfirmImport() {
  if (!extractedData.value) return
  uploading.value = true
  result.value = null
  try {
    // Convert extracted JSON array to CSV blob
    const rows = extractedData.value
    if (!rows.length) {
      $q.notify({ type: 'warning', message: 'Sem dados para importar' })
      return
    }
    const headers = Object.keys(rows[0] as Record<string, unknown>)
    const csvLines = [
      headers.join(','),
      ...rows.map((row) =>
        headers.map((h) => {
          const val = (row as Record<string, unknown>)[h]
          const str = val !== null && val !== undefined ? String(val) : ''
          return str.includes(',') ? `"${str}"` : str
        }).join(',')
      ),
    ]
    const csvBlob = new Blob([csvLines.join('\n')], { type: 'text/csv' })
    const csvFile = new File([csvBlob], 'import.csv', { type: 'text/csv' })

    const formData = new FormData()
    formData.append('file', csvFile)
    if (props.extraParams) {
      for (const [key, val] of Object.entries(props.extraParams)) {
        if (val !== null && val !== undefined) {
          formData.append(key, String(val))
        }
      }
    }
    const { data } = await api.post(props.endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = data
    tab.value = 'file'
    $q.notify({ type: 'positive', message: `Importação concluída: ${data.created} criados, ${data.skipped} ignorados` })
    if (data.created > 0) emit('done')
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    $q.notify({ type: 'negative', message: error.response?.data?.detail ?? 'Erro ao confirmar importação' })
  } finally {
    uploading.value = false
  }
}
</script>
