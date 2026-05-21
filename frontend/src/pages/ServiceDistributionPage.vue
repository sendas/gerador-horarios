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
        <q-btn color="primary" icon="download" label="Exportar CSV" dense :disable="teachers.length === 0" @click="exportCsv" />
        <q-btn color="secondary" icon="upload" label="Importar Comp. Letiva" dense :disable="!selectedYearId" @click="showImport = true" />
        <q-btn color="teal-7" icon="tune" label="Componentes" dense :disable="!selectedYearId" @click="openComponentDialog" />
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
    <div v-if="teachers.length > 0" class="row items-center q-mb-sm">
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
    </div>
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
      :filter="search"
      sort-by="name"
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

    <!-- Component management dialog -->
    <q-dialog v-model="showComponents" persistent style="max-width:900px">
      <q-card style="min-width:min(96vw,860px)">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6"><q-icon name="tune" class="q-mr-sm" />Gerir Componentes Letivas</div>
          <q-space /><q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <!-- Bulk actions bar -->
          <div class="row q-gutter-sm q-mb-md items-center">
            <q-btn color="teal-7" icon="playlist_add_check" label="Definir 22h a todos" unelevated @click="setAllBase(22)" :loading="bulkLoading" />
            <q-btn color="indigo-6" icon="elderly" label="Aplicar Art. 79° a todos" unelevated @click="applyArt79All" :loading="bulkLoading"
              :disable="compRows.every(r => !r.birth_date)" />
            <q-chip dense icon="info" color="blue-2" text-color="dark">
              Art. 79° ECD: 50–54a → −1h · 55–59a → −2h · ≥60a → −3h
            </q-chip>
          </div>

          <!-- Per-teacher table -->
          <q-table
            :rows="compRows"
            :columns="compColumns"
            row-key="id"
            flat dense
            :pagination="{ rowsPerPage: 0 }"
            hide-bottom
            style="max-height:60vh;overflow-y:auto"
            virtual-scroll
            :virtual-scroll-item-size="48"
          >
            <template #body-cell-birth_date="props">
              <q-td :props="props">
                <q-input
                  v-model="props.row.birth_date"
                  type="date"
                  dense outlined
                  style="min-width:140px"
                  @update:model-value="recalcRow(props.row)"
                />
              </q-td>
            </template>
            <template #body-cell-age="props">
              <q-td :props="props" class="text-center">
                <span v-if="props.row.birth_date">{{ calcAge(props.row.birth_date) }}</span>
                <span v-else class="text-grey-5">—</span>
              </q-td>
            </template>
            <template #body-cell-reduction="props">
              <q-td :props="props" class="text-center">
                <div class="row no-wrap items-center justify-center q-gutter-xs">
                  <q-input
                    v-model.number="props.row.reduction"
                    type="number" min="0" max="20"
                    dense outlined
                    style="width:60px"
                    @update:model-value="onReductionChange(props.row)"
                  />
                  <q-icon
                    v-if="props.row.reduction_manual"
                    name="edit" size="xs" color="orange-6"
                  >
                    <q-tooltip>Redução manual</q-tooltip>
                  </q-icon>
                  <q-icon
                    v-else-if="props.row.birth_date && props.row.reduction > 0"
                    name="auto_awesome" size="xs" color="indigo-4"
                  >
                    <q-tooltip>Calculado pelo Art. 79°</q-tooltip>
                  </q-icon>
                </div>
              </q-td>
            </template>
            <template #body-cell-component="props">
              <q-td :props="props" class="text-center">
                <q-input
                  v-model.number="props.row.teaching_component"
                  type="number" min="0" max="30"
                  dense outlined
                  style="width:70px"
                  @update:model-value="onComponentChange(props.row)"
                />
              </q-td>
            </template>
          </q-table>
        </q-card-section>

        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn color="teal-7" icon="save" label="Guardar" :loading="bulkLoading" @click="saveComponents" />
        </q-card-actions>
      </q-card>
    </q-dialog>
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

interface CompRow {
  id: number
  name: string
  birth_date: string | null
  base: number               // implicit base (usually 22); teaching_component + reduction = base
  reduction: number          // hours of reduction (Art.79° auto or manual)
  reduction_manual: boolean  // true = user typed reduction directly
  teaching_component: number | null
}

interface TimetableOption {
  id: number
  name: string
}

// ── State ────────────────────────────────────────────────────────────────────

const search = ref('')
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

// Component management dialog
const showComponents = ref(false)
const compRows = ref<CompRow[]>([])
const bulkLoading = ref(false)

const compColumns = [
  { name: 'name', label: 'Professor', field: 'name', align: 'left' as const, sortable: true },
  { name: 'birth_date', label: 'Data de Nasc.', field: 'birth_date', align: 'center' as const },
  { name: 'age', label: 'Idade', field: 'birth_date', align: 'center' as const },
  { name: 'reduction', label: 'Redução (h)', field: 'reduction', align: 'center' as const },
  { name: 'component', label: 'Comp. Letiva (h)', field: 'teaching_component', align: 'center' as const },
]

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

// ── Component management ──────────────────────────────────────────────────────

function calcAge(birthDateStr: string): number {
  const today = new Date()
  const bd = new Date(birthDateStr)
  let age = today.getFullYear() - bd.getFullYear()
  if (today.getMonth() < bd.getMonth() || (today.getMonth() === bd.getMonth() && today.getDate() < bd.getDate())) age--
  return age
}

function calcArt79(birthDateStr: string): number {
  const age = calcAge(birthDateStr)
  if (age >= 60) return 3
  if (age >= 55) return 2
  if (age >= 50) return 1
  return 0
}

function recalcRow(row: CompRow) {
  if (row.birth_date && !row.reduction_manual) {
    row.reduction = calcArt79(row.birth_date)
    row.teaching_component = row.base - row.reduction
  }
}

function onReductionChange(row: CompRow) {
  row.reduction_manual = true
  row.teaching_component = row.base - row.reduction
}

function onComponentChange(row: CompRow) {
  // Keep base in sync so future reduction changes are relative to the new value
  row.base = (row.teaching_component ?? 0) + row.reduction
}

async function openComponentDialog() {
  if (!selectedClusterId.value) return
  bulkLoading.value = true
  try {
    const { data } = await api.get('/teachers', { params: { cluster_id: selectedClusterId.value } })
    compRows.value = (data as { id: number; name: string; birth_date: string | null; teaching_component: number | null; credit_hours: number | null }[])
      .map(t => {
        const autoReduction = t.birth_date ? calcArt79(t.birth_date) : 0
        const reduction = t.credit_hours ?? autoReduction
        const reduction_manual = t.credit_hours !== null
        const base = t.teaching_component !== null ? t.teaching_component + reduction : 22
        return { id: t.id, name: t.name, birth_date: t.birth_date ?? null, base, reduction, reduction_manual, teaching_component: t.teaching_component ?? null }
      })
      .sort((a, b) => a.name.localeCompare(b.name))
  } finally {
    bulkLoading.value = false
  }
  showComponents.value = true
}

function setAllBase(base: number) {
  compRows.value.forEach(r => {
    r.base = base
    r.teaching_component = base - r.reduction
  })
}

function applyArt79All() {
  compRows.value.forEach(r => {
    if (r.birth_date) {
      r.reduction = calcArt79(r.birth_date)
      r.reduction_manual = false
      r.teaching_component = r.base - r.reduction
    }
  })
}

async function saveComponents() {
  bulkLoading.value = true
  try {
    const payload = compRows.value.map(r => ({
      id: r.id,
      teaching_component: r.teaching_component,
      birth_date: r.birth_date || null,
      credit_hours: r.reduction,
    }))
    await api.put('/teachers/bulk-update', payload)
    $q.notify({ type: 'positive', message: `${payload.length} professores atualizados` })
    showComponents.value = false
    await loadData()
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar componentes' })
  } finally {
    bulkLoading.value = false
  }
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
