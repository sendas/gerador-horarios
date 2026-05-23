<template>
  <q-page padding>
    <div class="text-h5 q-mb-md">Definição de horas por docente</div>

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

    <!-- School filter -->
    <div v-if="availableSchools.length > 1" class="row items-center q-mb-sm q-gutter-xs">
      <span class="text-caption text-grey-7 q-mr-xs">Filtrar por escola:</span>
      <q-chip
        v-for="school in availableSchools"
        :key="school.id"
        clickable
        :color="selectedSchoolId === school.id ? 'teal-7' : 'grey-3'"
        :text-color="selectedSchoolId === school.id ? 'white' : 'dark'"
        :icon="selectedSchoolId === school.id ? 'check' : undefined"
        :label="school.name"
        @click="selectedSchoolId = selectedSchoolId === school.id ? null : school.id"
      />
      <q-btn v-if="selectedSchoolId" flat dense size="sm" icon="close" color="grey-6" label="Limpar" @click="selectedSchoolId = null" />
    </div>

    <!-- Summary stats -->
    <div v-if="teachers.length > 0" class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-sm-4">
        <q-card flat bordered>
          <q-card-section class="text-center">
            <div class="text-h6">{{ filteredTeachers.length }}</div>
            <div class="text-caption text-grey-7">Professores{{ selectedSchoolId ? ' (filtrado)' : '' }}</div>
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
      :rows="filteredTeachers"
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
    <q-dialog v-model="showComponents" persistent maximized>
      <q-card>
        <q-card-section class="row items-center q-pb-sm bg-teal-8 text-white">
          <q-icon name="tune" size="sm" class="q-mr-sm" />
          <div class="text-h6">Definição de Horas por Docente</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup color="white" />
        </q-card-section>

        <!-- Legend -->
        <q-card-section class="q-py-sm bg-blue-grey-1">
          <div class="row q-gutter-md items-center text-caption text-grey-8 flex-wrap">
            <span><q-icon name="schedule" size="xs" color="teal-7" class="q-mr-xs" /><strong>H. Totais</strong> = horas de serviço total (35)</span>
            <span><q-icon name="school" size="xs" color="blue-7" class="q-mr-xs" /><strong>H. Letivas</strong> = componente letiva base (22)</span>
            <span><q-icon name="elderly" size="xs" color="indigo-6" class="q-mr-xs" /><strong>Red. Art.79°</strong> = 50–54a → 1h · 55–59a → 2h · ≥60a → 3h</span>
            <span><q-icon name="card_membership" size="xs" color="orange-7" class="q-mr-xs" /><strong>Crédito</strong> = horas de crédito por cargo</span>
            <span><q-icon name="calculate" size="xs" color="positive" class="q-mr-xs" /><strong>Comp. Letiva</strong> = H.Letivas − Red.Art.79° − Crédito</span>
          </div>
        </q-card-section>

        <q-card-section class="q-pt-sm q-pb-xs">
          <!-- Bulk actions -->
          <div class="row q-gutter-sm items-center flex-wrap">
            <q-btn color="blue-7" icon="school" label="Definir 22h letivas a todos" unelevated dense @click="setAllBase(22)" :loading="bulkLoading" />
            <q-btn color="indigo-6" icon="elderly" label="Aplicar Art. 79° a todos" unelevated dense @click="applyArt79All" :loading="bulkLoading"
              :disable="compRows.every(r => !r.birth_date)" />
            <q-input v-model="compSearch" placeholder="Pesquisar professor..." dense outlined clearable style="min-width:200px">
              <template #prepend><q-icon name="search" /></template>
            </q-input>
          </div>
        </q-card-section>

        <!-- Per-teacher table -->
        <q-card-section class="q-pt-xs" style="overflow:auto;height:calc(100vh - 220px)">
          <table class="comp-table">
            <thead>
              <tr>
                <th class="comp-th comp-th--name">Professor</th>
                <th class="comp-th">Data Nasc.</th>
                <th class="comp-th comp-th--sm">Idade</th>
                <th class="comp-th comp-th--sm">H. Totais</th>
                <th class="comp-th comp-th--sm">H. Letivas</th>
                <th class="comp-th comp-th--sm">Red. Art.79°</th>
                <th class="comp-th comp-th--sm">Crédito H.</th>
                <th class="comp-th comp-th--cargo">Cargo (crédito)</th>
                <th class="comp-th comp-th--sm">Comp. Letiva</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in filteredCompRows"
                :key="row.id"
                class="comp-row"
              >
                <td class="comp-td comp-td--name">{{ row.name }}</td>
                <td class="comp-td">
                  <q-input
                    v-model="row.birth_date"
                    type="date"
                    dense outlined
                    style="min-width:130px"
                    @update:model-value="onBirthDateChange(row)"
                  />
                </td>
                <td class="comp-td comp-td--center">
                  <span v-if="row.birth_date" class="text-body2">{{ calcAge(row.birth_date) }}</span>
                  <span v-else class="text-grey-5">—</span>
                </td>
                <td class="comp-td comp-td--center">
                  <q-input
                    v-model.number="row.total_hours"
                    type="number" min="1" max="50"
                    dense outlined
                    style="width:58px"
                    @update:model-value="recalcTeachingComponent(row)"
                  />
                </td>
                <td class="comp-td comp-td--center">
                  <q-input
                    v-model.number="row.base_teaching_hours"
                    type="number" min="0" max="40"
                    dense outlined
                    style="width:58px"
                    @update:model-value="recalcTeachingComponent(row)"
                  />
                </td>
                <td class="comp-td comp-td--center">
                  <div class="row no-wrap items-center justify-center" style="gap:4px">
                    <q-input
                      v-model.number="row.art79_reduction"
                      type="number" min="0" max="10"
                      dense outlined
                      style="width:54px"
                      @update:model-value="onArt79Change(row)"
                    />
                    <q-icon
                      v-if="row.art79_manual"
                      name="edit" size="xs" color="orange-6"
                    ><q-tooltip>Redução manual</q-tooltip></q-icon>
                    <q-icon
                      v-else-if="row.birth_date && row.art79_reduction > 0"
                      name="auto_awesome" size="xs" color="indigo-4"
                    ><q-tooltip>Calculado automaticamente pelo Art. 79°</q-tooltip></q-icon>
                  </div>
                </td>
                <td class="comp-td comp-td--center">
                  <q-input
                    v-model.number="row.credit_hours"
                    type="number" min="0" max="20"
                    dense outlined
                    style="width:54px"
                    @update:model-value="onCreditHoursChange(row)"
                  />
                </td>
                <td class="comp-td">
                  <q-select
                    v-model="row.credit_role"
                    :options="cargoOptions"
                    :disable="!row.credit_hours"
                    dense outlined
                    use-input hide-selected fill-input
                    input-debounce="0"
                    clearable
                    :placeholder="row.credit_hours ? 'Cargo...' : '—'"
                    style="min-width:180px"
                    @new-value="(val, done) => done(val)"
                  />
                </td>
                <td class="comp-td comp-td--center">
                  <q-badge
                    :color="row.teaching_component < 0 ? 'negative' : row.teaching_component === 0 ? 'grey-5' : 'positive'"
                    :label="row.teaching_component"
                    style="font-size:13px;padding:4px 8px"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </q-card-section>

        <q-card-actions align="right" class="q-px-md q-pb-md q-gutter-sm">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn color="teal-7" icon="save" label="Guardar tudo" :loading="bulkLoading" @click="saveComponents" />
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
  primary_school_id: number | null
  primary_school_name: string | null
}

interface CompRow {
  id: number
  name: string
  birth_date: string | null
  total_hours: number           // total service hours (default 35)
  base_teaching_hours: number   // base teaching component before reductions (default 22)
  art79_reduction: number       // Art.79° reduction (auto or manual)
  art79_manual: boolean         // true if user typed manually
  credit_hours: number          // credit hours (cargo-based)
  credit_role: string           // role description for credit hours
  teaching_component: number    // net teaching component = base - art79 - credit
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
const availableSchools = ref<{ id: number; name: string }[]>([])
const selectedSchoolId = ref<number | null>(null)
const expandedRows = ref<Set<number>>(new Set())

const showImport = ref(false)
const importFile = ref<File | null>(null)
const importLoading = ref(false)
const importResult = ref<{ updated: number; not_found: number; errors: string[] } | null>(null)

// Component management dialog
const showComponents = ref(false)
const compRows = ref<CompRow[]>([])
const compSearch = ref('')
const bulkLoading = ref(false)

const cargoOptions = [
  'Diretor de Turma',
  'Coordenador de Departamento',
  'Coordenador dos Diretores de Turma',
  'Assessor de Direção',
  'Representante de Grupo Disciplinar',
  'Coordenador de Projetos',
  'Dinamizador de Biblioteca / CRE',
  'Coordenador de Ano',
  'Orientador de Estágio',
  'Direção',
]

const filteredCompRows = computed(() => {
  if (!compSearch.value) return compRows.value
  const q = compSearch.value.toLowerCase()
  return compRows.value.filter((r) => r.name.toLowerCase().includes(q))
})

// ── Computed ─────────────────────────────────────────────────────────────────

const yearOptions = computed(() =>
  yearsStore.years.map((y) => ({ label: y.name, value: y.id }))
)

const selectedClusterId = computed(() => {
  const year = yearsStore.years.find((y) => y.id === selectedYearId.value)
  return year?.cluster_id ?? null
})

const filteredTeachers = computed(() => {
  if (!selectedSchoolId.value) return teachers.value
  return teachers.value.filter((t) => t.primary_school_id === selectedSchoolId.value)
})

const totalScheduledHours = computed(() =>
  filteredTeachers.value.reduce((sum, t) => sum + t.scheduled_hours, 0)
)

const averageScheduledHours = computed(() => {
  if (filteredTeachers.value.length === 0) return '—'
  return (totalScheduledHours.value / filteredTeachers.value.length).toFixed(1)
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
    availableSchools.value = (data.schools as { id: number; name: string }[]) ?? []
    selectedSchoolId.value = null
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

function recalcTeachingComponent(row: CompRow) {
  row.teaching_component = row.base_teaching_hours - row.art79_reduction - row.credit_hours
}

function onBirthDateChange(row: CompRow) {
  if (!row.art79_manual) {
    row.art79_reduction = row.birth_date ? calcArt79(row.birth_date) : 0
  }
  recalcTeachingComponent(row)
}

function onArt79Change(row: CompRow) {
  row.art79_manual = true
  recalcTeachingComponent(row)
}

function onCreditHoursChange(row: CompRow) {
  if (!row.credit_hours) row.credit_role = ''
  recalcTeachingComponent(row)
}

async function openComponentDialog() {
  if (!selectedClusterId.value) return
  bulkLoading.value = true
  compSearch.value = ''
  try {
    const { data } = await api.get('/teachers', { params: { cluster_id: selectedClusterId.value } })
    type ApiTeacher = {
      id: number; name: string; birth_date: string | null
      teaching_component: number | null; credit_hours: number | null; credit_role: string | null
      total_hours: number | null; base_teaching_hours: number | null
    }
    compRows.value = (data as ApiTeacher[]).map(t => {
      const base_teaching_hours = t.base_teaching_hours ?? 22
      const credit_hours = t.credit_hours ?? 0
      const total_hours = t.total_hours ?? 35
      const art79Auto = t.birth_date ? calcArt79(t.birth_date) : 0

      let art79_reduction: number
      let art79_manual: boolean
      if (t.teaching_component !== null) {
        // Derive art79 from stored values: NET = base - art79 - credit
        const derived = base_teaching_hours - t.teaching_component - credit_hours
        art79_reduction = Math.max(0, derived)
        art79_manual = art79_reduction !== art79Auto
      } else {
        art79_reduction = art79Auto
        art79_manual = false
      }

      const teaching_component = base_teaching_hours - art79_reduction - credit_hours
      return {
        id: t.id,
        name: t.name,
        birth_date: t.birth_date ?? null,
        total_hours,
        base_teaching_hours,
        art79_reduction,
        art79_manual,
        credit_hours,
        credit_role: t.credit_role ?? '',
        teaching_component,
      }
    }).sort((a, b) => a.name.localeCompare(b.name))
  } finally {
    bulkLoading.value = false
  }
  showComponents.value = true
}

function setAllBase(base: number) {
  compRows.value.forEach(r => {
    r.base_teaching_hours = base
    recalcTeachingComponent(r)
  })
}

function applyArt79All() {
  compRows.value.forEach(r => {
    if (r.birth_date) {
      r.art79_reduction = calcArt79(r.birth_date)
      r.art79_manual = false
      recalcTeachingComponent(r)
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
      credit_hours: r.credit_hours,
      credit_role: r.credit_role || null,
      total_hours: r.total_hours,
      base_teaching_hours: r.base_teaching_hours,
    }))
    await api.put('/teachers/bulk-update', payload)
    $q.notify({ type: 'positive', message: `${payload.length} professor(es) atualizados` })
    showComponents.value = false
    await loadData()
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar — tente novamente' })
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

<style scoped>
.comp-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
}
.comp-th {
  padding: 6px 8px;
  border: 1px solid #ccc;
  background: #2c3e50;
  color: white;
  text-align: center;
  white-space: nowrap;
  position: sticky;
  top: 0;
  z-index: 2;
}
.comp-th--name { text-align: left; min-width: 160px; }
.comp-th--sm { min-width: 70px; }
.comp-th--cargo { min-width: 200px; text-align: left; }
.comp-td {
  padding: 3px 6px;
  border: 1px solid #e0e0e0;
  vertical-align: middle;
}
.comp-td--name { font-weight: 500; white-space: nowrap; }
.comp-td--center { text-align: center; }
.comp-row:hover { background: rgba(0,0,0,0.03); }
.body--dark .comp-th { background: #1a2332; }
.body--dark .comp-td { border-color: #444; }
.body--dark .comp-row:hover { background: rgba(255,255,255,0.05); }
</style>
