<template>
  <q-page padding>
    <!-- Header -->
    <div class="row items-center q-mb-sm q-gutter-sm flex-wrap">
      <div class="text-h5 col">Atribuição de Professores por Turma</div>
      <q-chip v-if="unassignedCount > 0" color="warning" text-color="dark" icon="warning" :label="`${unassignedCount} sem professor`" />
      <q-chip v-else-if="allClasses.length > 0 && Object.keys(entriesByClassId).length > 0" color="positive" text-color="white" icon="check_circle" label="Todos atribuídos" />

      <!-- Auto-fill button -->
      <q-btn-dropdown unelevated color="teal" icon="auto_fix_high" label="Preencher auto" :loading="bulkRunning" dense>
        <q-list>
          <q-item clickable v-close-popup @click="startAutoFill(getVisibleClassIds())">
            <q-item-section avatar><q-icon name="done_all" color="teal" /></q-item-section>
            <q-item-section>
              <q-item-label>Preencher todos visíveis</q-item-label>
              <q-item-label caption>{{ getVisibleClassIds().length }} turmas</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup @click="showYearFillDialog = true">
            <q-item-section avatar><q-icon name="filter_list" color="teal" /></q-item-section>
            <q-item-section>
              <q-item-label>Por ano de escolaridade...</q-item-label>
            </q-item-section>
          </q-item>
          <q-separator />
          <q-item clickable v-close-popup @click="startAutoFill([...selectedClassIds])" :disable="selectedClassIds.size === 0">
            <q-item-section avatar><q-icon name="checklist" color="teal" /></q-item-section>
            <q-item-section>
              <q-item-label>Preencher selecionados</q-item-label>
              <q-item-label caption>{{ selectedClassIds.size }} turma(s) selecionada(s)</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>

      <!-- Clear button -->
      <q-btn-dropdown unelevated color="grey-7" icon="person_remove" label="Limpar" :loading="bulkRunning" dense>
        <q-list>
          <q-item clickable v-close-popup @click="confirmClear(getVisibleClassIds())">
            <q-item-section avatar><q-icon name="remove_done" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label>Limpar todos visíveis</q-item-label>
              <q-item-label caption>{{ getVisibleClassIds().length }} turmas</q-item-label>
            </q-item-section>
          </q-item>
          <q-separator />
          <q-item clickable v-close-popup @click="confirmClear([...selectedClassIds])" :disable="selectedClassIds.size === 0">
            <q-item-section avatar><q-icon name="checklist" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label>Limpar selecionados</q-item-label>
              <q-item-label caption>{{ selectedClassIds.size }} turma(s) selecionada(s)</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>

      <q-select
        v-model="selectedYearId"
        :options="yearOptions"
        label="Ano Letivo"
        emit-value map-options dense outlined
        style="min-width:180px"
        @update:model-value="load"
      />
    </div>

    <!-- School filter chips -->
    <div v-if="clusterSchools.length > 1" class="q-mb-md row q-gutter-xs items-center">
      <span class="text-caption text-grey-6 q-mr-xs">Escola:</span>
      <q-chip
        v-for="s in clusterSchools"
        :key="s.id"
        clickable dense
        :color="selectedSchoolIds.has(s.id) ? 'primary' : 'grey-3'"
        :text-color="selectedSchoolIds.has(s.id) ? 'white' : 'dark'"
        @click="toggleSchool(s.id)"
      >{{ s.name }}</q-chip>
      <q-btn v-if="selectedSchoolIds.size > 0" flat dense size="xs" icon="clear" color="grey" @click="selectedSchoolIds.clear()" />
    </div>

    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner size="40px" color="primary" /><div class="q-mt-sm text-grey">A carregar...</div>
    </div>

    <div v-else class="row q-col-gutter-md" style="min-height:600px">

      <!-- ── Left: class list ───────────────────────────────── -->
      <div class="col-12 col-md-3">
        <q-input v-model="classSearch" dense outlined clearable placeholder="Pesquisar turma..." class="q-mb-xs">
          <template #prepend><q-icon name="search" /></template>
        </q-input>

        <!-- Selection controls -->
        <div class="row items-center q-mb-xs q-gutter-xs">
          <q-btn flat dense size="xs" icon="select_all" label="Selec. todos" color="teal"
            @click="selectAllVisible" />
          <q-btn v-if="selectedClassIds.size > 0" flat dense size="xs" icon="deselect" label="Limpar sel." color="grey-6"
            @click="selectedClassIds.clear()" />
          <q-space />
          <q-badge v-if="selectedClassIds.size > 0" color="teal" :label="`${selectedClassIds.size} sel.`" />
        </div>

        <q-list bordered separator style="border-radius:6px;overflow:hidden">
          <template v-for="group in classesGrouped" :key="group.school_id">
            <q-item-label header class="bg-grey-2 text-grey-8 text-caption text-weight-bold q-py-xs">
              <q-icon name="school" size="xs" class="q-mr-xs" />{{ group.school_name }}
            </q-item-label>
            <q-item
              v-for="cls in group.classes"
              :key="cls.id"
              clickable v-ripple
              :active="selectedClassId === cls.id"
              active-color="primary"
              @click="selectClass(cls.id)"
            >
              <q-item-section avatar style="min-width:32px">
                <q-checkbox
                  :model-value="selectedClassIds.has(cls.id)"
                  dense size="sm"
                  color="teal"
                  @click.stop
                  @update:model-value="toggleClassSelection(cls.id)"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ cls.name }}</q-item-label>
                <q-item-label caption>{{ cls.year_level }}.º ano</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge
                  v-if="entriesByClassId[cls.id] && countUnassigned(cls.id) > 0"
                  color="warning" text-color="dark"
                  :label="countUnassigned(cls.id)"
                />
                <q-badge
                  v-else-if="entriesByClassId[cls.id]?.length"
                  color="positive" icon="check" label=""
                />
              </q-item-section>
            </q-item>
          </template>
          <q-item v-if="classesGrouped.length === 0">
            <q-item-section class="text-grey-5 text-caption">
              {{ allClasses.length === 0 ? 'Sem turmas para este ano letivo' : 'Nenhuma turma corresponde ao filtro' }}
            </q-item-section>
          </q-item>
        </q-list>
      </div>

      <!-- ── Right: subject + teacher ──────────────────────── -->
      <div class="col-12 col-md-9">
        <div v-if="!selectedClassId" class="text-center text-grey q-pa-xl">
          <q-icon name="group" size="64px" color="grey-3" />
          <div class="q-mt-sm">Selecione uma turma para gerir as disciplinas e professores</div>
        </div>

        <template v-else>
          <div class="row items-center q-mb-md">
            <div class="text-h6 col">
              <q-icon name="group" color="primary" class="q-mr-xs" />
              {{ selectedClass?.name }}
              <q-badge color="grey-5" :label="`${selectedEntries.length} disciplinas`" class="q-ml-sm" />
            </div>
            <q-btn color="primary" icon="add" label="Adicionar disciplina" dense unelevated @click="openAddSubject" />
          </div>

          <q-card flat bordered>
            <q-list separator>
              <q-item v-if="loadingEntries" class="justify-center q-py-md">
                <q-spinner color="primary" />
              </q-item>

              <q-item v-else-if="!selectedEntries.length" class="text-grey-5 text-caption">
                <q-item-section>Sem disciplinas. Adicione disciplinas com o botão acima.</q-item-section>
              </q-item>

              <q-item v-for="entry in selectedEntries" :key="entry.id" class="q-py-sm">
                <q-item-section>
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <span class="text-weight-medium">{{ entry.subject_name }}</span>
                    <q-badge color="blue-2" text-color="dark" :label="`${entry.hours_per_week}h/sem`" />
                  </div>
                  <div class="row items-center q-gutter-sm">
                    <q-chip
                      v-if="entry.teacher_id"
                      dense removable
                      color="positive" text-color="white"
                      icon="person"
                      :label="entry.teacher_name ?? ''"
                      @remove="assignTeacher(entry, null)"
                    />
                    <span v-else class="text-caption text-orange-8">
                      <q-icon name="person_off" size="xs" /> Sem professor
                    </span>
                    <q-select
                      :model-value="null"
                      :options="teacherOptsForSubject(entry.subject_id)"
                      emit-value map-options
                      dense outlined
                      use-input input-debounce="0"
                      @filter="(val, update) => filterTeachersForSubject(val, update, entry.subject_id)"
                      :placeholder="entry.teacher_id ? 'Substituir professor...' : 'Atribuir professor...'"
                      style="min-width:220px"
                      clearable
                      @update:model-value="(v) => { if (v) assignTeacher(entry, v) }"
                    >
                      <template #prepend><q-icon name="search" size="xs" /></template>
                      <template #no-option>
                        <q-item><q-item-section class="text-grey-6 text-caption">Nenhum professor leciona esta disciplina</q-item-section></q-item>
                      </template>
                    </q-select>
                  </div>
                </q-item-section>
                <q-item-section side top>
                  <q-btn flat round dense icon="delete" color="negative" size="sm" @click="deleteEntry(entry)" />
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

    <!-- Year level auto-fill dialog -->
    <q-dialog v-model="showYearFillDialog">
      <q-card style="min-width:380px">
        <q-card-section class="row items-center">
          <div class="text-h6"><q-icon name="filter_list" class="q-mr-xs" color="teal" />Preencher por ano</div>
          <q-space /><q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <div class="text-caption text-grey-7 q-mb-sm">Selecione os anos de escolaridade a preencher automaticamente:</div>
          <div class="row q-gutter-sm flex-wrap">
            <q-chip
              v-for="yl in availableYearLevels"
              :key="yl"
              clickable dense square
              :color="fillYearLevels.has(yl) ? 'teal' : 'grey-3'"
              :text-color="fillYearLevels.has(yl) ? 'white' : 'dark'"
              :icon="fillYearLevels.has(yl) ? 'check' : 'radio_button_unchecked'"
              @click="toggleFillYear(yl)"
            >{{ yl }}.º ano</q-chip>
          </div>
          <div class="text-caption text-grey-6 q-mt-sm">
            <q-icon name="info" size="xs" class="q-mr-xs" />
            Só preenche entradas sem professor. Os já atribuídos não são alterados.
          </div>
        </q-card-section>
        <q-card-section class="row justify-end q-gutter-sm">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn
            color="teal" icon="auto_fix_high" label="Preencher"
            :disable="fillYearLevels.size === 0"
            :loading="bulkRunning"
            @click="startAutoFillByYear"
          />
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useClustersStore } from 'stores/clusters'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useTeachersStore } from 'stores/teachers'
import { useSubjectsStore } from 'stores/subjects'
import { useSchoolsStore } from 'stores/schools'
import { useClassesStore } from 'stores/classes'
import type { SchoolClass } from 'stores/classes'

const $q = useQuasar()
const clustersStore = useClustersStore()
const yearsStore = useAcademicYearsStore()
const teachersStore = useTeachersStore()
const subjectsStore = useSubjectsStore()
const schoolsStore = useSchoolsStore()
const classesStore = useClassesStore()

type Entry = {
  id: number
  class_id: number
  subject_id: number
  subject_name: string
  hours_per_week: number
  teacher_id: number | null
  teacher_name: string | null
}

const loading = ref(false)
const loadingEntries = ref(false)
const bulkRunning = ref(false)
const selectedYearId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const classSearch = ref('')
const selectedSchoolIds = reactive(new Set<number>())
const selectedClassIds = reactive(new Set<number>())

// Year-level auto-fill dialog
const showYearFillDialog = ref(false)
const fillYearLevels = reactive(new Set<number>())

// Curriculum entries keyed by class_id — populated on demand when a class is selected
const entriesByClassId = ref<Record<number, Entry[]>>({})

// Add subject dialog
const showAddSubject = ref(false)
const newSubjectId = ref<number | null>(null)
const newHours = ref(2)
const newTeacherId = ref<number | null>(null)
// Per-subject teacher options cache (updated by the filter function)
const teacherOptsBySubject = ref<Record<number, { label: string; value: number }[]>>({})
// Teacher options for the "add discipline" dialog (no subject filter)
const filteredTeacherOpts = ref<{ label: string; value: number }[]>([])
const availableSubjectOptions = ref<{ label: string; value: number }[]>([])

const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)

const clusterSchools = computed(() =>
  schoolsStore.schools.filter((s) => s.cluster_id === clusterId.value)
)

// All classes belonging to this cluster and the selected year
const allClasses = computed<SchoolClass[]>(() => {
  const schoolIds = new Set(clusterSchools.value.map((s) => s.id))
  return classesStore.classes.filter(
    (c) => c.academic_year_id === selectedYearId.value && schoolIds.has(c.school_id)
  )
})

function schoolName(schoolId: number) {
  return schoolsStore.schools.find((s) => s.id === schoolId)?.name ?? '—'
}

// Classes grouped by school, filtered by school chips and search
const classesGrouped = computed(() => {
  const txt = classSearch.value.toLowerCase()
  const filterSchool = selectedSchoolIds.size > 0

  const filtered = allClasses.value.filter((c) => {
    if (filterSchool && !selectedSchoolIds.has(c.school_id)) return false
    if (txt && !c.name.toLowerCase().includes(txt) && !String(c.year_level).includes(txt)) return false
    return true
  })

  const bySchool = new Map<number, SchoolClass[]>()
  for (const c of filtered) {
    if (!bySchool.has(c.school_id)) bySchool.set(c.school_id, [])
    bySchool.get(c.school_id)!.push(c)
  }

  return [...bySchool.entries()]
    .map(([schoolId, classes]) => ({
      school_id: schoolId,
      school_name: schoolName(schoolId),
      classes: classes.sort((a, b) => a.year_level - b.year_level || a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => a.school_name.localeCompare(b.school_name))
})

const selectedClass = computed<SchoolClass | null>(
  () => allClasses.value.find((c) => c.id === selectedClassId.value) ?? null
)

const selectedEntries = computed<Entry[]>(() =>
  (entriesByClassId.value[selectedClassId.value ?? -1] ?? [])
    .slice()
    .sort((a, b) => a.subject_name.localeCompare(b.subject_name))
)

// Counts for badges
const unassignedCount = computed(() =>
  Object.values(entriesByClassId.value).reduce(
    (sum, list) => sum + list.filter((e) => !e.teacher_id).length,
    0
  )
)

function countUnassigned(classId: number) {
  return (entriesByClassId.value[classId] ?? []).filter((e) => !e.teacher_id).length
}

function toggleSchool(id: number) {
  if (selectedSchoolIds.has(id)) selectedSchoolIds.delete(id)
  else selectedSchoolIds.add(id)
}

// Used by each subject row — filters to teachers who teach that subject
function teacherOptsForSubject(subjectId: number) {
  return teacherOptsBySubject.value[subjectId] ?? teachersStore.teachers
    .filter((t) => t.subject_ids?.includes(subjectId))
    .map((t) => ({ label: t.name, value: t.id }))
}

function filterTeachersForSubject(val: string, update: (fn: () => void) => void, subjectId: number) {
  update(() => {
    const txt = val.toLowerCase()
    const opts = teachersStore.teachers
      .filter((t) => t.subject_ids?.includes(subjectId) && (!txt || t.name.toLowerCase().includes(txt)))
      .map((t) => ({ label: t.name, value: t.id }))
    teacherOptsBySubject.value = { ...teacherOptsBySubject.value, [subjectId]: opts }
  })
}

// Used by the "add discipline" dialog — no subject filter
function filterTeachersFn(val: string, update: (fn: () => void) => void) {
  update(() => {
    const txt = val.toLowerCase()
    filteredTeacherOpts.value = teachersStore.teachers
      .filter((t) => !txt || t.name.toLowerCase().includes(txt))
      .map((t) => ({ label: t.name, value: t.id }))
  })
}

function filterSubjectsFn(val: string, update: (fn: () => void) => void) {
  update(() => {
    const txt = val.toLowerCase()
    const usedIds = new Set(selectedEntries.value.map((e) => e.subject_id))
    availableSubjectOptions.value = subjectsStore.subjects
      .filter((s) => !usedIds.has(s.id) && (!txt || s.name.toLowerCase().includes(txt)))
      .map((s) => ({ label: s.name, value: s.id }))
  })
}

async function loadClassEntries(classId: number) {
  loadingEntries.value = true
  try {
    type RawEntry = { id: number; class_id: number; subject_id: number; hours_per_week: number; teacher_id: number | null; teacher_name: string | null }
    const { data } = await api.get<RawEntry[]>(`/classes/${classId}/curriculum`)
    const mapped: Entry[] = data.map((e) => ({
      id: e.id,
      class_id: classId,
      subject_id: e.subject_id,
      subject_name: subjectsStore.subjects.find((s) => s.id === e.subject_id)?.name ?? `ID:${e.subject_id}`,
      hours_per_week: e.hours_per_week,
      teacher_id: e.teacher_id ?? null,
      teacher_name: e.teacher_name ?? null,
    }))
    entriesByClassId.value = { ...entriesByClassId.value, [classId]: mapped }
  } finally {
    loadingEntries.value = false
  }
}

async function selectClass(classId: number) {
  selectedClassId.value = classId
  filteredTeacherOpts.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
  teacherOptsBySubject.value = {}
  if (!entriesByClassId.value[classId]) {
    await loadClassEntries(classId)
  }
}

async function load() {
  if (!selectedYearId.value) return
  loading.value = true
  selectedClassId.value = null
  entriesByClassId.value = {}
  try {
    await classesStore.fetchAll({ academic_year_id: selectedYearId.value })
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
    message: `Remover "${entry.subject_name}" da turma?`,
    ok: { label: 'Remover', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    try {
      await api.delete(`/classes/curriculum/${entry.id}`)
      const list = entriesByClassId.value[entry.class_id] ?? []
      entriesByClassId.value = {
        ...entriesByClassId.value,
        [entry.class_id]: list.filter((e) => e.id !== entry.id),
      }
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
    const { data } = await api.post<{ id: number }>(`/classes/${selectedClassId.value}/curriculum`, {
      subject_id: newSubjectId.value,
      hours_per_week: newHours.value,
      teacher_id: newTeacherId.value ?? null,
    })
    const subj = subjectsStore.subjects.find((s) => s.id === newSubjectId.value)
    const teacher = teachersStore.teachers.find((t) => t.id === newTeacherId.value)
    const classId = selectedClassId.value
    const list = entriesByClassId.value[classId] ?? []
    entriesByClassId.value = {
      ...entriesByClassId.value,
      [classId]: [...list, {
        id: data.id,
        class_id: classId,
        subject_id: newSubjectId.value,
        subject_name: subj?.name ?? '',
        hours_per_week: newHours.value,
        teacher_id: newTeacherId.value ?? null,
        teacher_name: teacher?.name ?? null,
      }],
    }
    showAddSubject.value = false
    $q.notify({ type: 'positive', message: 'Disciplina adicionada' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao adicionar disciplina' })
  }
}

// ── Bulk operations ──────────────────────────────────────────────────────────

const availableYearLevels = computed(() =>
  [...new Set(allClasses.value.map((c) => c.year_level))].sort((a, b) => a - b)
)

function getVisibleClassIds(): number[] {
  return classesGrouped.value.flatMap((g) => g.classes.map((c) => c.id))
}

function toggleClassSelection(id: number) {
  if (selectedClassIds.has(id)) selectedClassIds.delete(id)
  else selectedClassIds.add(id)
}

function selectAllVisible() {
  getVisibleClassIds().forEach((id) => selectedClassIds.add(id))
}

function toggleFillYear(yl: number) {
  if (fillYearLevels.has(yl)) fillYearLevels.delete(yl)
  else fillYearLevels.add(yl)
}

async function assignTeacherSilent(entry: Entry, teacherId: number | null) {
  await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: teacherId })
  entry.teacher_id = teacherId
  entry.teacher_name = teacherId ? (teachersStore.teachers.find((t) => t.id === teacherId)?.name ?? null) : null
}

async function startAutoFill(classIds: number[]) {
  if (!classIds.length) return
  bulkRunning.value = true
  let filled = 0
  let skipped = 0
  try {
    for (const classId of classIds) {
      if (!entriesByClassId.value[classId]) await loadClassEntries(classId)
      for (const entry of entriesByClassId.value[classId] ?? []) {
        if (entry.teacher_id) continue
        const candidates = teachersStore.teachers.filter((t) => t.subject_ids?.includes(entry.subject_id))
        if (!candidates.length) { skipped++; continue }
        const teacher = candidates[Math.floor(Math.random() * candidates.length)]
        try { await assignTeacherSilent(entry, teacher.id); filled++ } catch { /* skip */ }
      }
    }
    $q.notify({ type: 'positive', message: `${filled} atribuição(ões) preenchida(s)${skipped ? `, ${skipped} sem professor disponível` : ''}` })
  } finally {
    bulkRunning.value = false
  }
}

async function startAutoFillByYear() {
  const ids = allClasses.value
    .filter((c) => fillYearLevels.has(c.year_level))
    .map((c) => c.id)
  showYearFillDialog.value = false
  await startAutoFill(ids)
}

function confirmClear(classIds: number[]) {
  if (!classIds.length) return
  $q.dialog({
    title: 'Limpar atribuições',
    message: `Remover todos os professores de ${classIds.length} turma(s)?`,
    ok: { label: 'Limpar', color: 'negative' },
    cancel: true,
  }).onOk(() => runClear(classIds))
}

async function runClear(classIds: number[]) {
  bulkRunning.value = true
  let cleared = 0
  try {
    for (const classId of classIds) {
      if (!entriesByClassId.value[classId]) await loadClassEntries(classId)
      for (const entry of entriesByClassId.value[classId] ?? []) {
        if (!entry.teacher_id) continue
        try { await assignTeacherSilent(entry, null); cleared++ } catch { /* skip */ }
      }
    }
    $q.notify({ type: 'info', message: `${cleared} atribuição(ões) removida(s)` })
  } finally {
    bulkRunning.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    clustersStore.fetchAll(),
    yearsStore.fetchAll(),
    teachersStore.fetchAll(),
    subjectsStore.fetchAll(),
    schoolsStore.fetchAll(),
  ])
  filteredTeacherOpts.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
  selectedYearId.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  if (selectedYearId.value) await load()
})
</script>
