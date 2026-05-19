<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">
        <q-icon name="upload_file" class="q-mr-sm" />
        Importar Currículo
      </div>
    </div>

    <q-card style="max-width: 780px">
      <q-card-section>
        <q-banner :class="$q.dark.isActive ? 'bg-blue-9' : 'bg-blue-1'" class="q-mb-md" rounded>
          <template #avatar><q-icon name="info" color="blue" /></template>
          Importa turmas, disciplinas, professores e o currículo completo a partir de um ficheiro CSV/Excel.
          <br /><br />
          <strong>Colunas esperadas:</strong>
          <code>ano</code>, <code>turma</code>, <code>disciplina</code>,
          <code>horas semana</code>, <code>professor</code>, <code>articulado</code>
        </q-banner>

        <div class="q-gutter-md">
          <q-select
            v-model="selectedCluster"
            :options="clusterOptions"
            label="Agrupamento *"
            outlined
            emit-value
            map-options
            :rules="[(v) => !!v || 'Obrigatório']"
            :disable="loading"
            @update:model-value="selectedSchool = null; selectedYear = null"
          />

          <q-select
            v-model="selectedSchool"
            :options="schoolOptions"
            label="Escola *"
            outlined
            emit-value
            map-options
            :disable="!selectedCluster || loading"
            :rules="[(v) => !!v || 'Obrigatório']"
          />

          <q-select
            v-model="selectedYear"
            :options="yearOptions"
            label="Ano Letivo *"
            outlined
            emit-value
            map-options
            :disable="!selectedCluster || loading"
            :rules="[(v) => !!v || 'Obrigatório']"
          />

          <q-file
            v-model="selectedFile"
            label="Ficheiro CSV ou Excel"
            outlined
            accept=".csv,.xlsx,.xls"
            :disable="loading"
            @update:model-value="onFileSelected"
          >
            <template #prepend><q-icon name="attach_file" /></template>
          </q-file>

          <!-- Class filter — shown after CSV is parsed -->
          <div v-if="parsedClasses.length > 0" class="q-mt-sm">
            <div class="text-subtitle2 q-mb-sm">
              <q-icon name="filter_list" class="q-mr-xs" />
              Filtrar turmas a importar
              <span class="text-caption text-grey-6 q-ml-sm">
                {{ selectedClasses.size }} de {{ parsedClasses.length }} selecionadas
              </span>
            </div>

            <!-- Prefix quick-select -->
            <div v-if="uniquePrefixes.length > 1" class="q-mb-sm">
              <div class="text-caption text-grey-6 q-mb-xs">Por escola (prefixo):</div>
              <div class="row q-gutter-xs">
                <q-chip
                  v-for="p in uniquePrefixes"
                  :key="p.prefix"
                  clickable
                  :color="isPrefixAllSelected(p.prefix) ? 'primary' : ($q.dark.isActive ? 'grey-7' : 'grey-3')"
                  :text-color="isPrefixAllSelected(p.prefix) ? 'white' : ($q.dark.isActive ? 'white' : 'dark')"
                  @click="togglePrefix(p.prefix)"
                >
                  {{ p.prefix }} ({{ p.count }})
                </q-chip>
              </div>
            </div>

            <!-- Year quick-select -->
            <div v-if="uniqueYears.length > 1" class="q-mb-sm">
              <div class="text-caption text-grey-6 q-mb-xs">Por ano de escolaridade:</div>
              <div class="row q-gutter-xs">
                <q-chip
                  v-for="y in uniqueYears"
                  :key="y.year"
                  clickable
                  :color="isYearAllSelected(y.year) ? 'deep-orange-6' : ($q.dark.isActive ? 'grey-7' : 'grey-3')"
                  :text-color="isYearAllSelected(y.year) ? 'white' : ($q.dark.isActive ? 'white' : 'dark')"
                  @click="toggleYear(y.year)"
                >
                  {{ y.year }}.º ano ({{ y.count }})
                </q-chip>
              </div>
            </div>

            <!-- Individual class list -->
            <div class="row q-gutter-xs q-mb-xs items-center">
              <q-btn flat dense size="sm" label="Selecionar todas" @click="selectAll" />
              <q-btn flat dense size="sm" label="Deselecionar todas" @click="deselectAll" />
            </div>
            <div
              class="class-list rounded-borders q-pa-sm"
              :class="$q.dark.isActive ? 'bg-grey-9' : 'bg-grey-2'"
              style="max-height: 220px; overflow-y: auto"
            >
              <div
                v-for="cls in parsedClasses"
                :key="cls.name"
                class="row items-center q-py-xs"
              >
                <q-checkbox
                  :model-value="selectedClasses.has(cls.name)"
                  :label="cls.name"
                  dense
                  @update:model-value="toggleClass(cls.name, $event)"
                />
                <q-badge
                  v-if="cls.prefix"
                  :color="$q.dark.isActive ? 'blue-grey-7' : 'blue-grey-3'"
                  :text-color="$q.dark.isActive ? 'white' : 'dark'"
                  class="q-ml-sm"
                >
                  {{ cls.prefix }}
                </q-badge>
                <span class="text-caption text-grey-6 q-ml-xs">Ano {{ cls.yearLevel }}</span>
              </div>
            </div>
          </div>

          <!-- Progress -->
          <div v-if="loading" class="q-mt-sm">
            <div class="row items-center q-mb-xs">
              <span class="text-caption col">{{ progressLabel }}</span>
              <span class="text-caption text-grey-6">{{ Math.round(progress * 100) }}%</span>
            </div>
            <q-linear-progress :value="progress" color="primary" rounded style="height: 10px" />
            <div class="text-caption text-grey-6 q-mt-xs">
              {{ progressStats }}
            </div>
          </div>

          <q-banner v-if="result" rounded :class="result.errors?.length ? ($q.dark.isActive ? 'bg-orange-9' : 'bg-orange-1') : ($q.dark.isActive ? 'bg-green-9' : 'bg-green-1')">
            <template #avatar>
              <q-icon :name="result.errors?.length ? 'warning' : 'check_circle'" :color="result.errors?.length ? 'warning' : 'positive'" />
            </template>
            <div class="text-weight-medium q-mb-xs">Importação concluída</div>
            <div class="text-body2">
              Entradas de currículo criadas: <strong>{{ result.created }}</strong><br />
              Ignoradas (já existiam): <strong>{{ result.skipped }}</strong><br />
              Turmas novas: <strong>{{ result.new_classes }}</strong> &nbsp;
              Disciplinas novas: <strong>{{ result.new_subjects }}</strong> &nbsp;
              Professores novos: <strong>{{ result.new_teachers }}</strong>
            </div>
            <ul v-if="result.errors?.length" class="q-mt-xs q-mb-none" style="max-height:200px;overflow-y:auto">
              <li v-for="(e, i) in result.errors" :key="i" class="text-caption text-negative">{{ e }}</li>
            </ul>
          </q-banner>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="q-px-md q-pb-md">
        <q-btn
          color="primary"
          icon="upload"
          label="Importar"
          :loading="loading"
          :disable="!selectedFile || !selectedCluster || !selectedSchool || !selectedYear || selectedClasses.size === 0"
          @click="upload"
        />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useClustersStore } from 'stores/clusters'
import { useSchoolsStore } from 'stores/schools'
import { useAcademicYearsStore } from 'stores/academicYears'

const $q = useQuasar()
const clustersStore = useClustersStore()
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()

const selectedCluster = ref<number | null>(null)
const selectedSchool = ref<number | null>(null)
const selectedYear = ref<number | null>(null)
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const progress = ref(0)
const progressProcessed = ref(0)
const progressTotal = ref(0)
const progressCreated = ref(0)
const progressSkipped = ref(0)

const result = ref<{
  created: number; skipped: number; new_classes: number;
  new_subjects: number; new_teachers: number; errors: string[]
} | null>(null)

interface ParsedClass {
  name: string
  yearLevel: number
  prefix: string
}

const parsedClasses = ref<ParsedClass[]>([])
const selectedClasses = ref(new Set<string>())

const clusterOptions = computed(() =>
  clustersStore.clusters.map((c) => ({ label: c.name, value: c.id }))
)
const schoolOptions = computed(() =>
  schoolsStore.schools
    .filter((s) => !selectedCluster.value || s.cluster_id === selectedCluster.value)
    .map((s) => ({ label: s.name, value: s.id }))
)
const yearOptions = computed(() =>
  yearsStore.years
    .filter((y) => !selectedCluster.value || y.cluster_id === selectedCluster.value)
    .map((y) => ({ label: y.name, value: y.id }))
)

const uniquePrefixes = computed(() => {
  const map = new Map<string, number>()
  for (const cls of parsedClasses.value) {
    if (cls.prefix) map.set(cls.prefix, (map.get(cls.prefix) ?? 0) + 1)
  }
  return Array.from(map.entries())
    .map(([prefix, count]) => ({ prefix, count }))
    .sort((a, b) => a.prefix.localeCompare(b.prefix))
})

const uniqueYears = computed(() => {
  const map = new Map<number, number>()
  for (const cls of parsedClasses.value) {
    if (cls.yearLevel > 0) map.set(cls.yearLevel, (map.get(cls.yearLevel) ?? 0) + 1)
  }
  return Array.from(map.entries())
    .map(([year, count]) => ({ year, count }))
    .sort((a, b) => a.year - b.year)
})

function isPrefixAllSelected(prefix: string) {
  return parsedClasses.value
    .filter((c) => c.prefix === prefix)
    .every((c) => selectedClasses.value.has(c.name))
}

function isYearAllSelected(year: number) {
  return parsedClasses.value
    .filter((c) => c.yearLevel === year)
    .every((c) => selectedClasses.value.has(c.name))
}

function togglePrefix(prefix: string) {
  const classes = parsedClasses.value.filter((c) => c.prefix === prefix)
  const allSelected = classes.every((c) => selectedClasses.value.has(c.name))
  const next = new Set(selectedClasses.value)
  for (const c of classes) {
    allSelected ? next.delete(c.name) : next.add(c.name)
  }
  selectedClasses.value = next
}

function toggleYear(year: number) {
  const classes = parsedClasses.value.filter((c) => c.yearLevel === year)
  const allSelected = classes.every((c) => selectedClasses.value.has(c.name))
  const next = new Set(selectedClasses.value)
  for (const c of classes) {
    allSelected ? next.delete(c.name) : next.add(c.name)
  }
  selectedClasses.value = next
}

function toggleClass(name: string, value: boolean) {
  const next = new Set(selectedClasses.value)
  value ? next.add(name) : next.delete(name)
  selectedClasses.value = next
}

function selectAll() {
  selectedClasses.value = new Set(parsedClasses.value.map((c) => c.name))
}

function deselectAll() {
  selectedClasses.value = new Set()
}

function extractPrefix(turma: string): string {
  const parts = turma.trim().split(/\s+/)
  if (parts.length >= 3) return parts[parts.length - 1].toUpperCase()
  return ''
}

function parseCsvLine(line: string, sep: string): string[] {
  const result: string[] = []
  let inQuote = false
  let current = ''
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      inQuote = !inQuote
    } else if (ch === sep && !inQuote) {
      result.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }
  result.push(current.trim())
  return result
}

async function parseFile(file: File) {
  parsedClasses.value = []
  selectedClasses.value = new Set()

  const text = await file.text()
  const lines = text.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length < 2) return

  const firstLine = lines[0]
  const sep = firstLine.split(';').length > firstLine.split(',').length ? ';' : ','

  const headers = parseCsvLine(firstLine, sep).map((h) =>
    h.replace(/^﻿/, '').toLowerCase()
  )
  const turmaIdx = headers.findIndex((h) => h === 'turma')
  const anoIdx = headers.findIndex((h) => h === 'ano')

  if (turmaIdx < 0) return

  const classMap = new Map<string, ParsedClass>()
  for (let i = 1; i < lines.length; i++) {
    const cols = parseCsvLine(lines[i], sep)
    const turma = (cols[turmaIdx] ?? '').trim()
    if (!turma) continue
    if (!classMap.has(turma)) {
      const anoRaw = anoIdx >= 0 ? (cols[anoIdx] ?? '') : ''
      const yearLevel = parseInt(anoRaw) || 0
      const prefix = extractPrefix(turma)
      classMap.set(turma, { name: turma, yearLevel, prefix })
    }
  }

  const classes = Array.from(classMap.values()).sort((a, b) => {
    if (a.yearLevel !== b.yearLevel) return a.yearLevel - b.yearLevel
    return a.name.localeCompare(b.name)
  })

  parsedClasses.value = classes
  selectedClasses.value = new Set(classes.map((c) => c.name))
}

function onFileSelected(file: File | null) {
  result.value = null
  parsedClasses.value = []
  selectedClasses.value = new Set()
  if (file && (file.name.endsWith('.csv') || file.name.endsWith('.CSV'))) {
    parseFile(file)
  }
}

const progressLabel = computed(() =>
  progressTotal.value > 0
    ? `A processar linha ${progressProcessed.value} de ${progressTotal.value}…`
    : 'A processar…'
)

const progressStats = computed(() =>
  `Criadas: ${progressCreated.value}  |  Ignoradas: ${progressSkipped.value}`
)

async function upload() {
  if (!selectedFile.value || !selectedCluster.value || !selectedSchool.value || !selectedYear.value) return
  loading.value = true
  progress.value = 0
  progressProcessed.value = 0
  progressTotal.value = 0
  progressCreated.value = 0
  progressSkipped.value = 0
  result.value = null

  const fd = new FormData()
  fd.append('file', selectedFile.value)
  fd.append('cluster_id', String(selectedCluster.value))
  fd.append('school_id', String(selectedSchool.value))
  fd.append('academic_year_id', String(selectedYear.value))

  if (parsedClasses.value.length > 0 && selectedClasses.value.size < parsedClasses.value.length) {
    fd.append('filter_classes', JSON.stringify(Array.from(selectedClasses.value)))
  }

  const token = localStorage.getItem('token')

  try {
    const response = await fetch('/api/v1/imports/curriculum/stream', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      $q.notify({ color: 'negative', message: (data as { detail?: string }).detail ?? 'Erro ao importar' })
      return
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.trim()) continue
        const update = JSON.parse(line) as {
          processed: number; total: number; created: number; skipped: number;
          new_classes: number; new_subjects: number; new_teachers: number;
          errors: string[]; done?: boolean
        }
        progressProcessed.value = update.processed
        progressTotal.value = update.total
        progressCreated.value = update.created
        progressSkipped.value = update.skipped
        progress.value = update.total > 0 ? update.processed / update.total : 0

        if (update.done) {
          result.value = {
            created: update.created,
            skipped: update.skipped,
            new_classes: update.new_classes,
            new_subjects: update.new_subjects,
            new_teachers: update.new_teachers,
            errors: update.errors,
          }
          $q.notify({ color: 'positive', message: `${update.created} entradas de currículo importadas` })
        }
      }
    }
  } catch {
    $q.notify({ color: 'negative', message: 'Erro de ligação durante a importação' })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    clustersStore.fetchAll(),
    schoolsStore.fetchAll(),
    yearsStore.fetchAll(),
  ])
})
</script>
