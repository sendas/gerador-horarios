<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Atribuição de Professores por Turma</div>
      <q-chip v-if="unassignedCount > 0" color="warning" text-color="dark" icon="warning" :label="`${unassignedCount} sem professor`" />
      <q-chip v-else-if="entries.length > 0" color="positive" text-color="white" icon="check_circle" label="Todos atribuídos" />
      <q-select
        v-model="selectedYearId"
        :options="yearOptions"
        label="Ano Letivo"
        emit-value map-options dense outlined
        class="q-ml-md"
        style="min-width:180px"
        @update:model-value="load"
      />
    </div>

    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner size="40px" color="primary" /><div class="q-mt-sm text-grey">A carregar...</div>
    </div>

    <div v-else class="row q-col-gutter-md" style="min-height:600px">

      <!-- ── Left: class list ───────────────────────────────── -->
      <div class="col-12 col-md-3">
        <q-input v-model="classSearch" dense outlined clearable placeholder="Pesquisar turma..." class="q-mb-sm">
          <template #prepend><q-icon name="search" /></template>
        </q-input>

        <q-list bordered separator style="border-radius:6px;overflow:hidden">
          <template v-for="school in classesGrouped" :key="school.school_name">
            <q-item-label header class="bg-grey-2 text-grey-8 text-caption text-weight-bold q-py-xs">
              <q-icon name="school" size="xs" class="q-mr-xs" />{{ school.school_name }}
            </q-item-label>
            <q-item
              v-for="cls in school.classes"
              :key="cls.class_id"
              clickable v-ripple
              :active="selectedClassId === cls.class_id"
              active-color="primary"
              @click="selectClass(cls.class_id)"
            >
              <q-item-section>
                <q-item-label>{{ cls.class_name }}</q-item-label>
                <q-item-label caption>{{ cls.year_level }}.º ano</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge v-if="cls.unassigned > 0" color="warning" text-color="dark" :label="cls.unassigned" />
                <q-badge v-else color="positive" icon="check" label="" />
              </q-item-section>
            </q-item>
          </template>
          <q-item v-if="classesGrouped.length === 0">
            <q-item-section class="text-grey-5 text-caption">Sem turmas</q-item-section>
          </q-item>
        </q-list>
      </div>

      <!-- ── Right: subject + teacher assignment ───────────── -->
      <div class="col-12 col-md-9">
        <div v-if="!selectedClassId" class="text-center text-grey q-pa-xl">
          <q-icon name="group" size="64px" color="grey-3" />
          <div class="q-mt-sm">Selecione uma turma para gerir as disciplinas e professores</div>
        </div>

        <template v-else>
          <div class="row items-center q-mb-md">
            <div class="text-h6 col">
              <q-icon name="group" color="primary" class="q-mr-xs" />
              {{ selectedClassName }}
              <q-badge color="grey-5" :label="`${selectedEntries.length} disciplinas`" class="q-ml-sm" />
            </div>
            <!-- Add discipline button -->
            <q-btn color="primary" icon="add" label="Adicionar disciplina" dense unelevated @click="openAddSubject" />
          </div>

          <!-- Subject rows -->
          <q-card flat bordered>
            <q-list separator>
              <q-item v-if="!selectedEntries.length" class="text-grey-5 text-caption">
                <q-item-section>Sem disciplinas. Adicione disciplinas com o botão acima.</q-item-section>
              </q-item>

              <q-item v-for="entry in selectedEntries" :key="entry.id" class="q-py-sm">
                <q-item-section>
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <span class="text-weight-medium">{{ entry.subject_name }}</span>
                    <q-badge color="blue-2" text-color="dark" :label="`${entry.hours_per_week}h/sem`" />
                  </div>
                  <!-- Teacher assignment -->
                  <div class="row items-center q-gutter-sm">
                    <q-chip
                      v-if="entry.teacher_id"
                      dense removable
                      color="positive" text-color="white"
                      icon="person"
                      :label="entry.teacher_name ?? ''"
                      @remove="assignTeacher(entry, null)"
                    />
                    <span v-else class="text-caption text-orange-8"><q-icon name="person_off" size="xs" /> Sem professor</span>

                    <q-select
                      :model-value="null"
                      :options="filteredTeacherOpts"
                      emit-value map-options
                      dense outlined
                      use-input input-debounce="0"
                      @filter="filterTeachersFn"
                      :placeholder="entry.teacher_id ? 'Substituir professor...' : 'Atribuir professor...'"
                      style="min-width:220px"
                      clearable
                      @update:model-value="(v) => { if (v) assignTeacher(entry, v) }"
                    >
                      <template #prepend><q-icon name="search" size="xs" /></template>
                    </q-select>
                  </div>
                </q-item-section>
                <q-item-section side top>
                  <q-btn flat round dense icon="delete" color="negative" size="sm" @click="deleteEntry(entry)" title="Remover disciplina da turma" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </template>
      </div>
    </div>

    <!-- Add subject dialog -->
    <q-dialog v-model="showAddSubject">
      <q-card style="min-width:400px">
        <q-card-section class="row items-center">
          <div class="text-h6">Adicionar disciplina</div>
          <q-space /><q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-select
            v-model="newSubjectId"
            :options="availableSubjectOptions"
            label="Disciplina *"
            emit-value map-options dense outlined
            use-input input-debounce="0"
            @filter="filterSubjectsFn"
            class="q-mb-sm"
          />
          <q-input v-model.number="newHours" label="Horas/semana *" type="number" min="1" max="10" dense outlined class="q-mb-sm" />
          <q-select
            v-model="newTeacherId"
            :options="filteredTeacherOpts"
            label="Professor (opcional)"
            emit-value map-options dense outlined clearable
            use-input input-debounce="0"
            @filter="filterTeachersFn"
          />
        </q-card-section>
        <q-card-section class="row justify-end q-gutter-sm">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn color="primary" label="Adicionar" :disable="!newSubjectId || !newHours" @click="addSubject" />
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useClustersStore } from 'stores/clusters'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useTeachersStore } from 'stores/teachers'
import { useSubjectsStore } from 'stores/subjects'

const $q = useQuasar()
const clustersStore = useClustersStore()
const yearsStore = useAcademicYearsStore()
const teachersStore = useTeachersStore()
const subjectsStore = useSubjectsStore()

type Entry = {
  id: number; class_id: number; class_name: string; year_level: number
  school_id: number | null; school_name: string
  subject_id: number; subject_name: string
  hours_per_week: number; teacher_id: number | null; teacher_name: string | null
}

const entries = ref<Entry[]>([])
const loading = ref(false)
const selectedYearId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const classSearch = ref('')
const teacherFilterText = ref('')
const subjectFilterText = ref('')

// Add subject dialog
const showAddSubject = ref(false)
const newSubjectId = ref<number | null>(null)
const newHours = ref(2)
const newTeacherId = ref<number | null>(null)

const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)

const unassignedCount = computed(() => entries.value.filter((e) => !e.teacher_id).length)

// Group classes by school with unassigned count
const classesGrouped = computed(() => {
  const classMap = new Map<number, { class_id: number; class_name: string; year_level: number; school_name: string; unassigned: number }>()
  for (const e of entries.value) {
    if (!classMap.has(e.class_id)) {
      classMap.set(e.class_id, { class_id: e.class_id, class_name: e.class_name, year_level: e.year_level, school_name: e.school_name || '—', unassigned: 0 })
    }
    if (!e.teacher_id) classMap.get(e.class_id)!.unassigned++
  }
  const txt = classSearch.value.toLowerCase()
  const classes = [...classMap.values()].filter((c) => !txt || c.class_name.toLowerCase().includes(txt))

  const schools = new Map<string, typeof classes>()
  for (const c of classes) {
    if (!schools.has(c.school_name)) schools.set(c.school_name, [])
    schools.get(c.school_name)!.push(c)
  }
  return [...schools.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([school_name, classes]) => ({ school_name, classes: classes.sort((a, b) => a.year_level - b.year_level || a.class_name.localeCompare(b.class_name)) }))
})

const selectedEntries = computed(() =>
  entries.value.filter((e) => e.class_id === selectedClassId.value)
    .sort((a, b) => a.subject_name.localeCompare(b.subject_name))
)

const selectedClassName = computed(() => selectedEntries.value[0]?.class_name ?? '')

// Teacher options with filtering
const filteredTeacherOpts = ref(teachersStore.teachers.map((t) => ({ label: t.name, value: t.id })))
function filterTeachersFn(val: string, update: (fn: () => void) => void) {
  update(() => {
    teacherFilterText.value = val
    const txt = val.toLowerCase()
    filteredTeacherOpts.value = teachersStore.teachers
      .filter((t) => !txt || t.name.toLowerCase().includes(txt))
      .map((t) => ({ label: t.name, value: t.id }))
  })
}

// Subject options for add dialog (exclude already assigned)
const availableSubjectOptions = ref(subjectsStore.subjects.map((s) => ({ label: s.name, value: s.id })))
function filterSubjectsFn(val: string, update: (fn: () => void) => void) {
  update(() => {
    const txt = val.toLowerCase()
    const usedIds = new Set(selectedEntries.value.map((e) => e.subject_id))
    availableSubjectOptions.value = subjectsStore.subjects
      .filter((s) => !usedIds.has(s.id) && (!txt || s.name.toLowerCase().includes(txt)))
      .map((s) => ({ label: s.name, value: s.id }))
  })
}

function selectClass(classId: number) {
  selectedClassId.value = classId
  // Reset teacher filter
  filteredTeacherOpts.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
}

async function load() {
  if (!clusterId.value || !selectedYearId.value) return
  loading.value = true
  selectedClassId.value = null
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
    await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: teacherId })
    entry.teacher_id = teacherId
    entry.teacher_name = teachersStore.teachers.find((t) => t.id === teacherId)?.name ?? null
    $q.notify({ type: teacherId ? 'positive' : 'info', message: teacherId ? 'Professor atribuído' : 'Professor removido', timeout: 1200 })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar' })
  }
}

async function deleteEntry(entry: Entry) {
  $q.dialog({
    title: 'Remover disciplina',
    message: `Remover "${entry.subject_name}" da turma "${entry.class_name}"?`,
    ok: { label: 'Remover', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    try {
      await api.delete(`/classes/curriculum/${entry.id}`)
      entries.value = entries.value.filter((e) => e.id !== entry.id)
      $q.notify({ type: 'positive', message: 'Disciplina removida' })
    } catch {
      $q.notify({ type: 'negative', message: 'Erro ao remover' })
    }
  })
}

function openAddSubject() {
  newSubjectId.value = null
  newHours.value = 2
  newTeacherId.value = null
  const usedIds = new Set(selectedEntries.value.map((e) => e.subject_id))
  availableSubjectOptions.value = subjectsStore.subjects
    .filter((s) => !usedIds.has(s.id))
    .map((s) => ({ label: s.name, value: s.id }))
  showAddSubject.value = true
}

async function addSubject() {
  if (!selectedClassId.value || !newSubjectId.value || !newHours.value) return
  try {
    const { data } = await api.post(`/classes/${selectedClassId.value}/curriculum`, {
      subject_id: newSubjectId.value,
      hours_per_week: newHours.value,
      teacher_id: newTeacherId.value ?? null,
    })
    const subj = subjectsStore.subjects.find((s) => s.id === newSubjectId.value)
    const teacher = teachersStore.teachers.find((t) => t.id === newTeacherId.value)
    const classEntry = selectedEntries.value[0]
    entries.value.push({
      id: data.id,
      class_id: selectedClassId.value,
      class_name: classEntry?.class_name ?? '',
      year_level: classEntry?.year_level ?? 0,
      school_id: classEntry?.school_id ?? null,
      school_name: classEntry?.school_name ?? '',
      subject_id: newSubjectId.value,
      subject_name: subj?.name ?? '',
      hours_per_week: newHours.value,
      teacher_id: newTeacherId.value ?? null,
      teacher_name: teacher?.name ?? null,
    })
    showAddSubject.value = false
    $q.notify({ type: 'positive', message: 'Disciplina adicionada' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao adicionar disciplina' })
  }
}

onMounted(async () => {
  await Promise.all([clustersStore.fetchAll(), yearsStore.fetchAll(), teachersStore.fetchAll(), subjectsStore.fetchAll()])
  filteredTeacherOpts.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
  selectedYearId.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  if (selectedYearId.value) await load()
})
</script>
