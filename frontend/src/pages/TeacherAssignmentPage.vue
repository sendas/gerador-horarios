<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm">
      <div class="text-h5 col">Atribuição de Professores</div>
      <q-chip v-if="unassignedCount > 0" color="warning" text-color="dark" icon="warning" :label="`${unassignedCount} sem professor`" />
      <q-chip v-else-if="entries.length > 0" color="positive" text-color="white" icon="check_circle" label="Todos atribuídos" />
    </div>

    <div class="row q-col-gutter-md q-mb-md items-center">
      <div class="col-12 col-sm-4">
        <q-select
          v-model="selectedYearId"
          :options="yearOptions"
          label="Ano Letivo"
          emit-value map-options dense outlined
          @update:model-value="load"
        />
      </div>
      <div class="col-12 col-sm-4">
        <q-input v-model="searchText" label="Filtrar turma, disciplina ou professor..." dense outlined clearable debounce="200">
          <template #prepend><q-icon name="search" /></template>
        </q-input>
      </div>
      <div class="col-12 col-sm-4">
        <q-toggle v-model="showOnlyUnassigned" label="Só sem professor" color="warning" @update:model-value="() => {}" />
      </div>
    </div>

    <q-table
      :rows="filteredEntries"
      :columns="columns"
      row-key="id"
      :loading="loading"
      :rows-per-page-options="[25, 50, 0]"
      flat bordered
      dense
    >
      <template #body="props">
        <q-tr :props="props" :class="props.row.teacher_id ? '' : 'bg-orange-1'">
          <q-td key="year_level" :props="props" class="text-center">
            <q-badge :color="yearColor(props.row.year_level)" :label="`${props.row.year_level}º`" />
          </q-td>
          <q-td key="class_name" :props="props">{{ props.row.class_name }}</q-td>
          <q-td key="subject_name" :props="props">{{ props.row.subject_name }}</q-td>
          <q-td key="hours_per_week" :props="props" class="text-center">{{ props.row.hours_per_week }}h</q-td>
          <q-td key="teacher" :props="props">
            <q-select
              :model-value="props.row.teacher_id"
              :options="teacherOptions"
              emit-value
              map-options
              dense
              clearable
              placeholder="— sem professor —"
              style="min-width:220px"
              @update:model-value="(v) => assignTeacher(props.row, v)"
            >
              <template #prepend>
                <q-icon :name="props.row.teacher_id ? 'person' : 'person_off'" :color="props.row.teacher_id ? 'positive' : 'warning'" size="xs" />
              </template>
            </q-select>
          </q-td>
        </q-tr>
      </template>

      <template #no-data>
        <div class="full-width text-center q-pa-lg text-grey-6">
          <q-icon name="search_off" size="2rem" class="q-mb-sm" />
          <div>{{ selectedYearId ? 'Nenhuma entrada encontrada.' : 'Selecione um ano letivo.' }}</div>
        </div>
      </template>
    </q-table>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useClustersStore } from 'stores/clusters'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useTeachersStore } from 'stores/teachers'

const $q = useQuasar()
const clustersStore = useClustersStore()
const yearsStore = useAcademicYearsStore()
const teachersStore = useTeachersStore()

type Entry = {
  id: number
  class_id: number
  class_name: string
  year_level: number
  subject_id: number
  subject_name: string
  hours_per_week: number
  teacher_id: number | null
  teacher_name: string | null
}

const entries = ref<Entry[]>([])
const loading = ref(false)
const selectedYearId = ref<number | null>(null)
const showOnlyUnassigned = ref(false)
const searchText = ref('')

const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)

const teacherOptions = computed(() =>
  teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
)

const unassignedCount = computed(() => entries.value.filter((e) => !e.teacher_id).length)

const filteredEntries = computed(() => {
  let result = entries.value
  if (showOnlyUnassigned.value) result = result.filter((e) => !e.teacher_id)
  if (searchText.value) {
    const txt = searchText.value.toLowerCase()
    result = result.filter(
      (e) =>
        e.class_name.toLowerCase().includes(txt) ||
        e.subject_name.toLowerCase().includes(txt) ||
        (e.teacher_name ?? '').toLowerCase().includes(txt),
    )
  }
  return result
})

const columns = [
  { name: 'year_level', label: 'Ano', field: 'year_level', align: 'center' as const, sortable: true },
  { name: 'class_name', label: 'Turma', field: 'class_name', align: 'left' as const, sortable: true },
  { name: 'subject_name', label: 'Disciplina', field: 'subject_name', align: 'left' as const, sortable: true },
  { name: 'hours_per_week', label: 'Horas/sem', field: 'hours_per_week', align: 'center' as const },
  { name: 'teacher', label: 'Professor', field: 'teacher_name', align: 'left' as const, sortable: true },
]

const yearColors = ['blue', 'teal', 'green', 'orange', 'purple', 'red', 'pink', 'brown', 'cyan']
function yearColor(year: number) { return yearColors[(year - 1) % yearColors.length] ?? 'grey' }

async function load() {
  if (!clusterId.value || !selectedYearId.value) return
  loading.value = true
  try {
    const { data } = await api.get<Entry[]>('/classes/curriculum-overview', {
      params: { cluster_id: clusterId.value, academic_year_id: selectedYearId.value },
    })
    entries.value = data
  } finally {
    loading.value = false
  }
}

async function assignTeacher(entry: Entry, teacherId: number | null) {
  try {
    await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: teacherId ?? null })
    entry.teacher_id = teacherId
    entry.teacher_name = teachersStore.teachers.find((t) => t.id === teacherId)?.name ?? null
    $q.notify({ type: 'positive', message: teacherId ? 'Professor atribuído' : 'Atribuição removida', timeout: 1200 })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar atribuição' })
  }
}

onMounted(async () => {
  await Promise.all([clustersStore.fetchAll(), yearsStore.fetchAll(), teachersStore.fetchAll()])
  selectedYearId.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  if (selectedYearId.value) await load()
})
</script>
