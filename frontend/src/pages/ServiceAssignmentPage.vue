<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Distribuição de Serviço</div>
      <q-select
        v-model="selectedYearId"
        :options="yearOptions"
        label="Ano Letivo"
        emit-value map-options
        dense outlined
        style="min-width:200px"
        @update:model-value="onYearChange"
      />
    </div>

    <div v-if="!selectedYearId" class="text-center text-grey q-pa-xl">
      <q-icon name="calendar_today" size="64px" color="grey-3" />
      <div class="q-mt-sm">Selecione um ano letivo para começar</div>
    </div>

    <div v-else class="row q-col-gutter-md">

      <!-- ── Left panel: teacher + hours ─────────────────── -->
      <div class="col-12 col-md-3">

        <!-- Teacher select -->
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey-7 q-mb-xs">PROFESSOR</div>
            <q-select
              v-model="selectedTeacherId"
              :options="filteredTeacherOptions"
              label="Escolher professor..."
              emit-value map-options
              dense outlined
              use-input
              input-debounce="0"
              @filter="filterTeachersFn"
              @update:model-value="onTeacherChange"
            />
          </q-card-section>

          <!-- Hours counter -->
          <template v-if="selectedTeacherId && selectedTeacher">
            <q-separator />
            <q-card-section class="text-center q-pb-xs">
              <div
                class="text-h2 text-weight-bold"
                :class="remainingHours < 0 ? 'text-negative' : remainingHours === 0 ? 'text-positive' : 'text-primary'"
              >
                {{ remainingHours }}h
              </div>
              <div class="text-caption text-grey">horas livres</div>
            </q-card-section>

            <q-card-section class="q-pt-xs">
              <q-linear-progress
                :value="progressRatio"
                :color="progressColor"
                track-color="grey-3"
                size="12px"
                rounded
                class="q-mb-sm"
              />
              <div class="row text-center q-gutter-none">
                <div class="col">
                  <div class="text-subtitle2">{{ totalHours }}h</div>
                  <div class="text-caption text-grey">Componente</div>
                </div>
                <div class="col">
                  <div class="text-subtitle2 text-blue-7">{{ assignedHours }}h</div>
                  <div class="text-caption text-grey">Letivo</div>
                </div>
                <div class="col">
                  <div class="text-subtitle2 text-orange-7">{{ creditHours }}h</div>
                  <div class="text-caption text-grey">Crédito</div>
                </div>
              </div>
            </q-card-section>

            <q-separator />
            <q-card-section>
              <div class="text-caption text-grey-7 q-mb-xs">Horas de crédito / redução</div>
              <q-input
                v-model.number="creditHours"
                type="number"
                min="0"
                step="0.5"
                dense outlined
                placeholder="0"
                hint="Ex: apoio à direção, coordenação..."
              />
            </q-card-section>
          </template>
        </q-card>

        <!-- Year level filter -->
        <q-card flat bordered class="q-mt-sm" v-if="selectedTeacherId">
          <q-card-section>
            <div class="text-caption text-grey-7 q-mb-xs">Filtrar por ano de escolaridade</div>
            <div class="row q-gutter-xs flex-wrap">
              <q-btn
                v-for="y in allYearLevels"
                :key="y"
                dense round outline size="sm"
                :color="yearFilter.has(y) ? 'primary' : 'grey-5'"
                :label="`${y}º`"
                @click="toggleYearFilter(y)"
              />
              <q-btn
                v-if="yearFilter.size > 0"
                dense round outline size="sm"
                color="grey-5"
                icon="clear"
                title="Remover filtros"
                @click="yearFilter = new Set()"
              />
            </div>

            <!-- Quick-select by cycle -->
            <div class="row q-gutter-xs q-mt-xs">
              <q-btn dense flat size="xs" color="blue-6" label="2.º ciclo (5-6)" @click="setCycle([5, 6])" />
              <q-btn dense flat size="xs" color="deep-purple-6" label="3.º ciclo (7-9)" @click="setCycle([7, 8, 9])" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- ── Right panel: subjects by school ─────────────── -->
      <div class="col-12 col-md-9">

        <div v-if="!selectedTeacherId" class="text-center text-grey q-pa-xl">
          <q-icon name="person" size="64px" color="grey-3" />
          <div class="q-mt-sm">Selecione um professor para ver as disciplinas disponíveis</div>
        </div>

        <div v-else-if="loadingSubjects" class="text-center q-pa-xl">
          <q-spinner size="40px" color="primary" />
          <div class="q-mt-sm text-grey">A carregar disciplinas...</div>
        </div>

        <div v-else-if="groupedBySchool.length === 0" class="text-center text-grey q-pa-xl">
          <q-icon name="book_off" size="48px" color="grey-3" />
          <div class="q-mt-sm">
            Nenhuma disciplina disponível para este professor neste ano letivo.<br>
            <small>Adicione disciplinas ao professor na página <strong>Professores → Disciplinas</strong>.</small>
          </div>
        </div>

        <template v-else>
          <q-card
            v-for="school in groupedBySchool"
            :key="school.school_name"
            flat bordered
            class="q-mb-md"
          >
            <!-- School header -->
            <div class="row items-center q-px-md q-py-sm bg-primary text-white">
              <q-icon name="school" size="sm" class="q-mr-sm" />
              <span class="text-subtitle1 text-weight-medium col">{{ school.school_name }}</span>
              <span class="text-caption opacity-80">{{ school.assignedHours }}h atribuídas</span>
            </div>

            <!-- Subject groups -->
            <q-expansion-item
              v-for="subject in school.subjects"
              :key="subject.subject_name"
              default-opened
              dense
              class="subject-block"
            >
              <template #header>
                <q-item-section>
                  <div class="row items-center q-gutter-xs">
                    <span class="text-weight-medium">{{ subject.subject_name }}</span>
                    <q-badge
                      :color="subject.assignedCount > 0 ? 'positive' : 'grey-4'"
                      :text-color="subject.assignedCount > 0 ? 'white' : 'dark'"
                      :label="`${subject.assignedCount}/${filteredSubjectEntries(subject.entries).length} turmas`"
                    />
                    <q-badge
                      v-if="subject.assignedHours > 0"
                      color="blue-6"
                      text-color="white"
                      :label="`${subject.assignedHours}h`"
                    />
                  </div>
                </q-item-section>
                <!-- Assign all button -->
                <q-item-section side>
                  <q-btn
                    flat dense round size="sm"
                    icon="done_all"
                    color="positive"
                    title="Atribuir todas as turmas visíveis"
                    :loading="assigningAll === subject.subject_name"
                    @click.stop="assignAll(subject)"
                  />
                </q-item-section>
              </template>

              <q-list dense separator>
                <q-item
                  v-for="entry in filteredSubjectEntries(subject.entries)"
                  :key="entry.id"
                  clickable
                  v-ripple
                  :class="isAssigned(entry) ? 'bg-green-1' : entry.teacher_id ? 'bg-orange-1' : ''"
                  @click="toggleAssign(entry)"
                >
                  <q-item-section avatar style="min-width:36px">
                    <q-checkbox
                      :model-value="isAssigned(entry)"
                      :color="isAssigned(entry) ? 'positive' : 'grey'"
                      dense
                      @click.stop
                      @update:model-value="() => toggleAssign(entry)"
                    />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="row items-center q-gutter-xs">
                      <span>{{ entry.class_name }}</span>
                      <q-badge
                        :color="yearBadgeColor(entry.year_level)"
                        :label="`${entry.year_level}º`"
                        size="xs"
                      />
                    </q-item-label>
                    <!-- Show who is currently assigned if it's not this teacher -->
                    <q-item-label caption v-if="entry.teacher_id && !isAssigned(entry)" class="text-orange-8">
                      <q-icon name="person" size="xs" />
                      Atribuído a: {{ entry.teacher_name }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-badge
                      :color="isAssigned(entry) ? 'positive' : 'blue-2'"
                      :text-color="isAssigned(entry) ? 'white' : 'dark'"
                      :label="`${entry.hours_per_week}h`"
                    />
                  </q-item-section>
                </q-item>

                <q-item v-if="filteredSubjectEntries(subject.entries).length === 0">
                  <q-item-section class="text-grey-5 text-caption">Nenhuma turma para o ano selecionado</q-item-section>
                </q-item>
              </q-list>
            </q-expansion-item>
          </q-card>
        </template>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
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
  school_id: number | null
  school_name: string
  subject_id: number
  subject_name: string
  hours_per_week: number
  teacher_id: number | null
  teacher_name: string | null
}

// ── State ──────────────────────────────────────────────
const selectedYearId = ref<number | null>(null)
const selectedTeacherId = ref<number | null>(null)
const allEntries = ref<Entry[]>([])
const teacherSubjectIds = ref<number[]>([])
const creditHours = ref(0)
const yearFilter = ref<Set<number>>(new Set())
const loadingSubjects = ref(false)
const teacherFilterText = ref('')
const assigningAll = ref<string | null>(null)

// ── Computed ───────────────────────────────────────────
const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)

const yearOptions = computed(() =>
  yearsStore.years.map((y) => ({ label: y.name, value: y.id }))
)

const selectedTeacher = computed(() =>
  teachersStore.teachers.find((t) => t.id === selectedTeacherId.value) ?? null
)

const filteredTeacherOptions = ref(
  teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
)

function filterTeachersFn(val: string, update: (fn: () => void) => void) {
  update(() => {
    teacherFilterText.value = val
    const txt = val.toLowerCase()
    filteredTeacherOptions.value = teachersStore.teachers
      .filter((t) => t.name.toLowerCase().includes(txt))
      .map((t) => ({ label: t.name, value: t.id }))
  })
}

const assignedHours = computed(() => {
  if (!selectedTeacherId.value) return 0
  return allEntries.value
    .filter((e) => e.teacher_id === selectedTeacherId.value)
    .reduce((sum, e) => sum + e.hours_per_week, 0)
})

const totalHours = computed(() => selectedTeacher.value?.teaching_component ?? 0)
const usedHours = computed(() => assignedHours.value + creditHours.value)
const remainingHours = computed(() => totalHours.value - usedHours.value)

const progressRatio = computed(() =>
  totalHours.value > 0 ? Math.min(1, usedHours.value / totalHours.value) : 0
)

const progressColor = computed(() => {
  if (remainingHours.value < 0) return 'negative'
  if (remainingHours.value === 0) return 'positive'
  if (progressRatio.value > 0.85) return 'warning'
  return 'primary'
})

const allYearLevels = computed(() => {
  const years = new Set(allEntries.value.map((e) => e.year_level))
  return [...years].sort((a, b) => a - b)
})

// Entries for teacher's subjects, grouped by school → subject
const groupedBySchool = computed(() => {
  if (!selectedTeacherId.value || teacherSubjectIds.value.length === 0) return []

  const relevant = allEntries.value.filter((e) =>
    teacherSubjectIds.value.includes(e.subject_id)
  )

  const schoolMap = new Map<string, Map<string, Entry[]>>()
  for (const entry of relevant) {
    const sn = entry.school_name || entry.class_name.split(' ').pop() || 'Outras'
    if (!schoolMap.has(sn)) schoolMap.set(sn, new Map())
    const subjMap = schoolMap.get(sn)!
    if (!subjMap.has(entry.subject_name)) subjMap.set(entry.subject_name, [])
    subjMap.get(entry.subject_name)!.push(entry)
  }

  return [...schoolMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([school_name, subjMap]) => {
      const subjects = [...subjMap.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([subject_name, entries]) => {
          const sorted = [...entries].sort(
            (a, b) => a.year_level - b.year_level || a.class_name.localeCompare(b.class_name)
          )
          const assignedEntries = sorted.filter((e) => e.teacher_id === selectedTeacherId.value)
          return {
            subject_name,
            entries: sorted,
            assignedCount: assignedEntries.length,
            assignedHours: assignedEntries.reduce((s, e) => s + e.hours_per_week, 0),
          }
        })
      const schoolAssignedHours = subjects.reduce((s, sub) => s + sub.assignedHours, 0)
      return { school_name, subjects, assignedHours: schoolAssignedHours }
    })
})

// ── Helpers ────────────────────────────────────────────
function filteredSubjectEntries(entries: Entry[]) {
  if (yearFilter.value.size === 0) return entries
  return entries.filter((e) => yearFilter.value.has(e.year_level))
}

function isAssigned(entry: Entry) {
  return entry.teacher_id === selectedTeacherId.value
}

function toggleYearFilter(y: number) {
  const s = new Set(yearFilter.value)
  s.has(y) ? s.delete(y) : s.add(y)
  yearFilter.value = s
}

function setCycle(years: number[]) {
  yearFilter.value = new Set(years)
}

const yearColors = ['blue', 'teal', 'green', 'orange', 'purple', 'red', 'pink', 'brown', 'cyan']
function yearBadgeColor(y: number) {
  return yearColors[(y - 1) % yearColors.length] ?? 'grey'
}

// ── Actions ────────────────────────────────────────────
async function onYearChange() {
  allEntries.value = []
  selectedTeacherId.value = null
  teacherSubjectIds.value = []
  creditHours.value = 0
  yearFilter.value = new Set()
  if (!selectedYearId.value || !clusterId.value) return

  await Promise.all([
    clustersStore.fetchAll(),
    yearsStore.fetchAll(),
    teachersStore.fetchAll(),
  ])

  const { data } = await api.get<Entry[]>('/classes/curriculum-overview', {
    params: { cluster_id: clusterId.value, academic_year_id: selectedYearId.value },
  })
  allEntries.value = data

  // Reset teacher filter options
  filteredTeacherOptions.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
}

async function onTeacherChange() {
  teacherSubjectIds.value = []
  creditHours.value = 0
  yearFilter.value = new Set()
  if (!selectedTeacherId.value) return
  loadingSubjects.value = true
  try {
    const { data } = await api.get(`/teachers/${selectedTeacherId.value}/subjects`)
    teacherSubjectIds.value = (data as { subject_id: number }[]).map((ts) => ts.subject_id)
  } finally {
    loadingSubjects.value = false
  }
}

async function toggleAssign(entry: Entry) {
  if (!selectedTeacherId.value) return
  const newTeacherId = isAssigned(entry) ? null : selectedTeacherId.value
  try {
    await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: newTeacherId })
    entry.teacher_id = newTeacherId
    entry.teacher_name = newTeacherId
      ? (teachersStore.teachers.find((t) => t.id === newTeacherId)?.name ?? null)
      : null
    $q.notify({
      type: newTeacherId ? 'positive' : 'info',
      message: newTeacherId ? `+${entry.hours_per_week}h — ${entry.class_name}` : `−${entry.hours_per_week}h — ${entry.class_name}`,
      timeout: 1000,
    })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar atribuição' })
  }
}

async function assignAll(subject: { subject_name: string; entries: Entry[] }) {
  if (!selectedTeacherId.value) return
  const toAssign = filteredSubjectEntries(subject.entries).filter(
    (e) => !isAssigned(e) && !e.teacher_id
  )
  if (toAssign.length === 0) return
  assigningAll.value = subject.subject_name
  for (const entry of toAssign) {
    await toggleAssign(entry)
  }
  assigningAll.value = null
}

// Initialize
import { onMounted } from 'vue'
onMounted(async () => {
  await Promise.all([clustersStore.fetchAll(), yearsStore.fetchAll(), teachersStore.fetchAll()])
  filteredTeacherOptions.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
  selectedYearId.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  if (selectedYearId.value) await onYearChange()
})
</script>

<style scoped>
.subject-block {
  border-top: 1px solid rgba(0,0,0,0.08);
}
.body--dark .subject-block {
  border-top-color: rgba(255,255,255,0.08);
}
</style>
