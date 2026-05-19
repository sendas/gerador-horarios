<template>
  <q-page padding>
    <div class="text-h5 q-mb-md">Distribuição de Serviço</div>

    <!-- Selectors + actions -->
    <div class="row q-col-gutter-md q-mb-md items-end">
      <div class="col-12 col-sm-4">
        <q-select
          v-model="selectedYearId"
          :options="yearOptions"
          label="Ano Letivo"
          emit-value
          map-options
          dense
          outlined
          @update:model-value="onYearChange"
        />
      </div>
      <div class="col-12 col-sm-4">
        <q-select
          v-model="selectedTimetableId"
          :options="timetableOptions"
          label="Horário"
          emit-value
          map-options
          dense
          outlined
          :disable="!selectedYearId"
          clearable
          @update:model-value="onTimetableChange"
        />
      </div>
      <div class="col-12 col-sm-4 row items-center q-gutter-sm">
        <q-btn
          color="primary"
          icon="download"
          label="Exportar CSV"
          dense
          :disable="teachers.length === 0"
          @click="exportCsv"
        />
        <q-btn
          color="secondary"
          icon="upload"
          label="Importar Comp. Letiva"
          dense
          :disable="!selectedYearId"
          @click="showImport = true"
        />
      </div>
    </div>

    <!-- Import dialog -->
    <q-dialog v-model="showImport">
      <q-card style="min-width: 420px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Importar Componentes Letivas</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-banner :class="$q.dark.isActive ? 'bg-blue-9' : 'bg-blue-1'" rounded class="q-mb-md">
            <template #avatar><q-icon name="info" color="blue" /></template>
            Importa a <strong>Componente Letiva</strong> de cada professor a partir de um ficheiro CSV/Excel.
            <br /><br />
            <strong>Colunas esperadas:</strong> <code>professor</code> (ou <code>nome</code>)
            e <code>comp. letiva</code> (ou <code>teaching_component</code>).
            <br />
            <span class="text-caption">O ficheiro exportado por esta página pode ser reimportado após edição.</span>
          </q-banner>

          <q-file
            v-model="importFile"
            label="Ficheiro CSV ou Excel"
            outlined
            accept=".csv,.xlsx,.xls"
            :disable="importLoading"
          >
            <template #prepend><q-icon name="attach_file" /></template>
          </q-file>

          <q-linear-progress v-if="importLoading" indeterminate color="primary" class="q-mt-sm" />

          <q-banner
            v-if="importResult"
            rounded
            :class="importResult.errors?.length ? ($q.dark.isActive ? 'bg-orange-9' : 'bg-orange-1') : ($q.dark.isActive ? 'bg-green-9' : 'bg-green-1')"
            class="q-mt-md"
          >
            <template #avatar>
              <q-icon
                :name="importResult.errors?.length ? 'warning' : 'check_circle'"
                :color="importResult.errors?.length ? 'warning' : 'positive'"
              />
            </template>
            <div class="text-weight-medium q-mb-xs">Importação concluída</div>
            <div class="text-body2">
              Professores atualizados: <strong>{{ importResult.updated }}</strong><br />
              Não encontrados: <strong>{{ importResult.not_found }}</strong>
            </div>
            <ul v-if="importResult.errors?.length" class="q-mt-xs q-mb-none" style="max-height:140px;overflow-y:auto">
              <li v-for="(e, i) in importResult.errors" :key="i" class="text-caption text-negative">{{ e }}</li>
            </ul>
          </q-banner>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn flat label="Fechar" v-close-popup />
          <q-btn
            color="primary"
            icon="upload"
            label="Importar"
            :loading="importLoading"
            :disable="!importFile"
            @click="doImport"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Summary stats -->
    <div v-if="teachers.length > 0" class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-sm-4">
        <q-card flat bordered>
          <q-card-section class="text-center">
            <div class="text-h6">{{ teachers.length }}</div>
            <div class="text-caption text-grey-7">Professores</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-4">
        <q-card flat bordered>
          <q-card-section class="text-center">
            <div class="text-h6">{{ totalScheduledHours }}</div>
            <div class="text-caption text-grey-7">Total Horas Marcadas</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-4">
        <q-card flat bordered>
          <q-card-section class="text-center">
            <div class="text-h6">{{ averageScheduledHours }}</div>
            <div class="text-caption text-grey-7">Média Horas Marcadas</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading" class="text-center q-py-xl text-grey-6">
      <q-icon name="event_busy" size="64px" class="q-mb-sm" />
      <div class="text-h6">
        {{
          !selectedYearId
            ? 'Selecione um Ano Letivo'
            : !selectedTimetableId
            ? 'Selecione um Horário para ver a distribuição'
            : 'Sem dados disponíveis'
        }}
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-center q-py-xl">
      <q-spinner size="48px" color="primary" />
    </div>

    <!-- Main table -->
    <q-table
      v-if="teachers.length > 0"
      :rows="teachers"
      :columns="columns"
      row-key="id"
      flat
      bordered
      dense
      :pagination="{ rowsPerPage: 0 }"
      hide-bottom
    >
      <template #body="props">
        <q-tr :props="props" @click="toggleExpand(props.row)" class="cursor-pointer">
          <q-td
            v-for="col in columns"
            :key="col.name"
            :props="props"
            :class="col.classes"
          >
            <template v-if="col.name === 'teaching_component'">
              <q-badge
                :color="componentColor(props.row)"
                :label="props.row.teaching_component ?? '—'"
              />
            </template>

            <template v-else-if="col.name === 'scheduled_hours'">
              <span :class="scheduledHoursClass(props.row)">
                {{ props.row.scheduled_hours }}
              </span>
            </template>

            <template v-else-if="col.name === 'classes_taught'">
              <template v-if="props.row.classes_taught.length === 0">
                <span class="text-grey-5">—</span>
              </template>
              <template v-else>
                <q-chip
                  v-for="ct in props.row.classes_taught.slice(0, 3)"
                  :key="ct.class_name + ct.subject_name"
                  dense
                  size="sm"
                  :color="$q.dark.isActive ? 'blue-grey-7' : 'blue-grey-2'"
                  :text-color="$q.dark.isActive ? 'white' : 'dark'"
                >
                  {{ ct.class_name }} · {{ ct.subject_name }}
                </q-chip>
                <q-chip
                  v-if="props.row.classes_taught.length > 3"
                  dense
                  size="sm"
                  :color="$q.dark.isActive ? 'grey-7' : 'grey-4'"
                  :text-color="$q.dark.isActive ? 'white' : 'dark'"
                >
                  +{{ props.row.classes_taught.length - 3 }}
                </q-chip>
              </template>
            </template>

            <template v-else>
              {{ col.field instanceof Function ? col.field(props.row) : props.row[col.field as keyof TeacherDistribution] }}
            </template>
          </q-td>
        </q-tr>

        <!-- Expanded detail row -->
        <q-tr v-if="expandedRows.has(props.row.id)" :props="props">
          <q-td colspan="100%" :class="$q.dark.isActive ? 'bg-blue-grey-9' : 'bg-blue-grey-1'">
            <div class="q-pa-sm">
              <div class="text-subtitle2 q-mb-sm">Turmas e Disciplinas — {{ props.row.name }}</div>
              <q-markup-table dense flat bordered style="max-width: 560px">
                <thead>
                  <tr>
                    <th class="text-left">Turma</th>
                    <th class="text-left">Disciplina</th>
                    <th class="text-right">H/Semana</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="ct in props.row.classes_taught" :key="ct.class_name + ct.subject_name">
                    <td>{{ ct.class_name }}</td>
                    <td>{{ ct.subject_name }}</td>
                    <td class="text-right">{{ ct.hours_per_week }}</td>
                  </tr>
                </tbody>
              </q-markup-table>
            </div>
          </q-td>
        </q-tr>
      </template>
    </q-table>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAcademicYearsStore } from 'stores/academicYears'

const $q = useQuasar()
const yearsStore = useAcademicYearsStore()

// ── Types ────────────────────────────────────────────────────────────────────

interface ClassTaught {
  class_name: string
  subject_name: string
  hours_per_week: number
}

interface TeacherDistribution {
  id: number
  name: string
  teaching_component: number | null
  scheduled_hours: number
  non_teaching_hours: number
  total_service: number
  classes_taught: ClassTaught[]
}

interface TimetableOption {
  id: number
  name: string
}

// ── State ────────────────────────────────────────────────────────────────────

const loading = ref(false)
const selectedYearId = ref<number | null>(null)
const selectedTimetableId = ref<number | null>(null)
const teachers = ref<TeacherDistribution[]>([])
const timetableOptions = ref<{ label: string; value: number }[]>([])
const expandedRows = ref<Set<number>>(new Set())

const showImport = ref(false)
const importFile = ref<File | null>(null)
const importLoading = ref(false)
const importResult = ref<{ updated: number; not_found: number; errors: string[] } | null>(null)

// ── Computed ─────────────────────────────────────────────────────────────────

const yearOptions = computed(() =>
  yearsStore.years.map((y) => ({ label: y.name, value: y.id }))
)

const selectedClusterId = computed(() => {
  const year = yearsStore.years.find((y) => y.id === selectedYearId.value)
  return year?.cluster_id ?? null
})

const totalScheduledHours = computed(() =>
  teachers.value.reduce((sum, t) => sum + t.scheduled_hours, 0)
)

const averageScheduledHours = computed(() => {
  if (teachers.value.length === 0) return '—'
  return (totalScheduledHours.value / teachers.value.length).toFixed(1)
})

// ── Columns ───────────────────────────────────────────────────────────────────

const columns = [
  { name: 'name', label: 'Professor', field: 'name', align: 'left' as const, sortable: true, classes: 'text-left' },
  { name: 'teaching_component', label: 'Comp. Letiva', field: 'teaching_component', align: 'center' as const, sortable: true, classes: 'text-center' },
  { name: 'scheduled_hours', label: 'Horas Marcadas', field: 'scheduled_hours', align: 'center' as const, sortable: true, classes: 'text-center' },
  { name: 'non_teaching_hours', label: 'Serv. Não Letivo', field: 'non_teaching_hours', align: 'center' as const, sortable: true, classes: 'text-center' },
  { name: 'total_service', label: 'Total Serviço', field: 'total_service', align: 'center' as const, sortable: true, classes: 'text-center' },
  { name: 'classes_taught', label: 'Turmas', field: 'classes_taught', align: 'left' as const, classes: 'text-left' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function componentColor(row: TeacherDistribution): string {
  if (row.teaching_component === null) return 'grey'
  if (row.scheduled_hours > row.teaching_component) return 'negative'
  if (row.scheduled_hours >= row.teaching_component * 0.9) return 'positive'
  return 'warning'
}

function scheduledHoursClass(row: TeacherDistribution): string {
  if (row.teaching_component === null) return ''
  if (row.scheduled_hours > row.teaching_component) return 'text-negative text-weight-bold'
  if (row.scheduled_hours >= row.teaching_component * 0.9) return 'text-positive text-weight-bold'
  return 'text-warning text-weight-bold'
}

function toggleExpand(row: TeacherDistribution) {
  if (expandedRows.value.has(row.id)) {
    expandedRows.value.delete(row.id)
  } else {
    expandedRows.value.add(row.id)
  }
  expandedRows.value = new Set(expandedRows.value)
}

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadData() {
  if (!selectedYearId.value) return
  loading.value = true
  expandedRows.value = new Set()
  try {
    const params: Record<string, number> = { academic_year_id: selectedYearId.value }
    if (selectedTimetableId.value) params.timetable_id = selectedTimetableId.value
    const { data } = await api.get('/service-distribution', { params })
    teachers.value = data.teachers as TeacherDistribution[]
    timetableOptions.value = (data.timetables as TimetableOption[]).map((t) => ({ label: t.name, value: t.id }))
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao carregar distribuição de serviço' })
    teachers.value = []
  } finally {
    loading.value = false
  }
}

// ── Import ────────────────────────────────────────────────────────────────────

async function doImport() {
  if (!importFile.value || !selectedClusterId.value) return
  importLoading.value = true
  importResult.value = null
  try {
    const fd = new FormData()
    fd.append('file', importFile.value)
    fd.append('cluster_id', String(selectedClusterId.value))
    const { data } = await api.post('/imports/teaching-components', fd)
    importResult.value = data
    $q.notify({ color: 'positive', message: `${data.updated} professores atualizados` })
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    $q.notify({ color: 'negative', message: err.response?.data?.detail ?? 'Erro ao importar' })
  } finally {
    importLoading.value = false
  }
}

// ── Event handlers ────────────────────────────────────────────────────────────

async function onYearChange() {
  selectedTimetableId.value = null
  timetableOptions.value = []
  teachers.value = []
  expandedRows.value = new Set()
  await loadData()
}

async function onTimetableChange() {
  await loadData()
}

// ── Export CSV ────────────────────────────────────────────────────────────────

function exportCsv() {
  const header = ['Professor', 'Comp. Letiva', 'Horas Marcadas', 'Serv. Não Letivo', 'Total Serviço', 'Turmas']
  const rows = teachers.value.map((t) => [
    t.name,
    t.teaching_component ?? '',
    t.scheduled_hours,
    t.non_teaching_hours,
    t.total_service,
    t.classes_taught.map((ct) => `${ct.class_name} ${ct.subject_name} (${ct.hours_per_week}h)`).join(' | '),
  ])
  const csvContent = [header, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob(['﻿' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', 'distribuicao-servico.csv')
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  await yearsStore.fetchAll()
  const activeYear = yearsStore.years.find((y) => y.is_active)
  if (activeYear) {
    selectedYearId.value = activeYear.id
    await loadData()
  }
})
</script>
