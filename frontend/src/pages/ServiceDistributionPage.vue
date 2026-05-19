<template>
  <q-page padding>
    <div class="text-h5 q-mb-md">Distribuição de Serviço</div>

    <!-- Selectors -->
    <div class="row q-col-gutter-md q-mb-md">
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
      </div>
    </div>

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
      <!-- Teaching component badge -->
      <template #body-cell-teaching_component="props">
        <q-td :props="props" class="text-center">
          <q-badge
            :color="componentColor(props.row)"
            :label="props.row.teaching_component ?? '—'"
          />
        </q-td>
      </template>

      <!-- Scheduled hours -->
      <template #body-cell-scheduled_hours="props">
        <q-td :props="props" class="text-center">
          <span :class="scheduledHoursClass(props.row)">
            {{ props.row.scheduled_hours }}
          </span>
        </q-td>
      </template>

      <!-- Classes taught as chips with expansion -->
      <template #body-cell-classes_taught="props">
        <q-td :props="props">
          <template v-if="props.row.classes_taught.length === 0">
            <span class="text-grey-5">—</span>
          </template>
          <template v-else>
            <q-chip
              v-for="ct in props.row.classes_taught.slice(0, 2)"
              :key="ct.class_name + ct.subject_name"
              dense
              size="sm"
              color="blue-grey-2"
              text-color="dark"
            >
              {{ ct.class_name }} · {{ ct.subject_name }}
            </q-chip>
            <q-chip
              v-if="props.row.classes_taught.length > 2"
              dense
              size="sm"
              color="grey-4"
              text-color="dark"
              @click="expandRow(props.row)"
              clickable
            >
              +{{ props.row.classes_taught.length - 2 }} mais
            </q-chip>
          </template>
        </q-td>
      </template>

      <!-- Row expansion -->
      <template #body="props">
        <q-tr :props="props" @click="toggleExpand(props.row)" class="cursor-pointer">
          <q-td
            v-for="col in columns"
            :key="col.name"
            :props="props"
            :class="col.classes"
          >
            <!-- teaching_component -->
            <template v-if="col.name === 'teaching_component'">
              <q-badge
                :color="componentColor(props.row)"
                :label="props.row.teaching_component ?? '—'"
              />
            </template>

            <!-- scheduled_hours -->
            <template v-else-if="col.name === 'scheduled_hours'">
              <span :class="scheduledHoursClass(props.row)">
                {{ props.row.scheduled_hours }}
              </span>
            </template>

            <!-- classes_taught -->
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
                  color="blue-grey-2"
                  text-color="dark"
                >
                  {{ ct.class_name }} · {{ ct.subject_name }}
                </q-chip>
                <q-chip
                  v-if="props.row.classes_taught.length > 3"
                  dense
                  size="sm"
                  color="grey-4"
                  text-color="dark"
                >
                  +{{ props.row.classes_taught.length - 3 }}
                </q-chip>
              </template>
            </template>

            <!-- default -->
            <template v-else>
              {{ col.field instanceof Function ? col.field(props.row) : props.row[col.field as keyof TeacherDistribution] }}
            </template>
          </q-td>
        </q-tr>

        <!-- Expanded detail row -->
        <q-tr v-if="expandedRows.has(props.row.id)" :props="props">
          <q-td colspan="100%" class="bg-blue-grey-1">
            <div class="q-pa-sm">
              <div class="text-subtitle2 q-mb-sm">Turmas e Disciplinas — {{ props.row.name }}</div>
              <q-markup-table dense flat bordered class="bg-white" style="max-width: 560px">
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

// ── Computed ─────────────────────────────────────────────────────────────────

const yearOptions = computed(() =>
  yearsStore.years.map((y) => ({ label: y.name, value: y.id }))
)

const totalScheduledHours = computed(() =>
  teachers.value.reduce((sum, t) => sum + t.scheduled_hours, 0)
)

const averageScheduledHours = computed(() => {
  if (teachers.value.length === 0) return '—'
  return (totalScheduledHours.value / teachers.value.length).toFixed(1)
})

// ── Columns ───────────────────────────────────────────────────────────────────

const columns = [
  {
    name: 'name',
    label: 'Professor',
    field: 'name',
    align: 'left' as const,
    sortable: true,
    classes: 'text-left',
  },
  {
    name: 'teaching_component',
    label: 'Comp. Letiva',
    field: 'teaching_component',
    align: 'center' as const,
    sortable: true,
    classes: 'text-center',
  },
  {
    name: 'scheduled_hours',
    label: 'Horas Marcadas',
    field: 'scheduled_hours',
    align: 'center' as const,
    sortable: true,
    classes: 'text-center',
  },
  {
    name: 'non_teaching_hours',
    label: 'Serv. Não Letivo',
    field: 'non_teaching_hours',
    align: 'center' as const,
    sortable: true,
    classes: 'text-center',
  },
  {
    name: 'total_service',
    label: 'Total Serviço',
    field: 'total_service',
    align: 'center' as const,
    sortable: true,
    classes: 'text-center',
  },
  {
    name: 'classes_taught',
    label: 'Turmas',
    field: 'classes_taught',
    align: 'left' as const,
    classes: 'text-left',
  },
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
  // Trigger Vue reactivity on the Set
  expandedRows.value = new Set(expandedRows.value)
}

function expandRow(row: TeacherDistribution) {
  expandedRows.value.add(row.id)
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

    // Update timetable selector options
    timetableOptions.value = (data.timetables as TimetableOption[]).map((t) => ({
      label: t.name,
      value: t.id,
    }))
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Erro ao carregar distribuição de serviço' })
    teachers.value = []
  } finally {
    loading.value = false
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
  const header = [
    'Professor',
    'Comp. Letiva',
    'Horas Marcadas',
    'Serv. Não Letivo',
    'Total Serviço',
    'Turmas',
  ]

  const rows = teachers.value.map((t) => [
    t.name,
    t.teaching_component ?? '',
    t.scheduled_hours,
    t.non_teaching_hours,
    t.total_service,
    t.classes_taught.map((ct) => `${ct.class_name} ${ct.subject_name} (${ct.hours_per_week}h)`).join(' | '),
  ])

  const csvContent = [header, ...rows]
    .map((row) =>
      row
        .map((cell) => `"${String(cell).replace(/"/g, '""')}"`)
        .join(',')
    )
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
