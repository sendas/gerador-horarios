<template>
  <q-page padding>
    <!-- Header -->
    <div class="row items-center q-mb-sm q-gutter-sm flex-wrap">
      <div class="text-h5 col">Atribuição de Professores</div>
      <q-chip v-if="unassignedCount > 0" color="warning" text-color="dark" icon="warning" :label="`${unassignedCount} sem professor`" />
      <q-chip v-else-if="allEntries.length > 0" color="positive" text-color="white" icon="check_circle" label="Todos atribuídos" />

      <q-btn
        outline color="orange-8" icon="sync" label="Sincronizar disciplinas"
        :loading="syncing"
        :disable="!selectedYearId"
        @click="syncFromPlans"
      >
        <q-tooltip>Aplica os planos curriculares a todas as turmas, criando as disciplinas em falta</q-tooltip>
      </q-btn>

      <q-btn
        flat dense round icon="analytics"
        :color="showHoursPanel ? 'teal-7' : 'grey-5'"
        @click="showHoursPanel = !showHoursPanel"
      >
        <q-tooltip>{{ showHoursPanel ? 'Ocultar' : 'Mostrar' }} painel de saldo de horas</q-tooltip>
      </q-btn>

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
        v-for="s in clusterSchools" :key="s.id"
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

      <!-- ── Left: class list ─────────────────────────────── -->
      <div class="col-12 col-md-3">
        <q-input v-model="classSearch" dense outlined clearable placeholder="Pesquisar turma..." class="q-mb-xs">
          <template #prepend><q-icon name="search" /></template>
        </q-input>

        <q-list bordered separator style="border-radius:6px;overflow:hidden">
          <template v-for="group in classesGrouped" :key="group.school_id">
            <q-item-label header class="bg-grey-2 text-grey-8 text-caption text-weight-bold q-py-xs">
              <q-icon name="school" size="xs" class="q-mr-xs" />{{ group.school_name }}
            </q-item-label>
            <q-item
              v-for="cls in group.classes" :key="cls.id"
              clickable v-ripple
              :active="selectedClassId === cls.id"
              active-color="primary"
              @click="selectClass(cls.id)"
            >
              <q-item-section>
                <q-item-label>{{ cls.name }}</q-item-label>
                <q-item-label caption>{{ cls.year_level }}.º ano</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge v-if="countUnassigned(cls.id) > 0" color="warning" text-color="dark" :label="countUnassigned(cls.id)" />
                <q-icon v-else-if="(entriesByClassId[cls.id]?.length ?? 0) > 0" name="check_circle" color="positive" size="sm" />
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

      <!-- ── Middle: class detail ─────────────────────────── -->
      <div :class="showHoursPanel ? 'col-12 col-md-5' : 'col-12 col-md-9'">
        <div v-if="!selectedClassId" class="text-center text-grey q-pa-xl">
          <q-icon name="group" size="64px" color="grey-3" />
          <div class="q-mt-sm">Selecione uma turma para atribuir professores</div>
        </div>

        <template v-else>
          <div class="row items-center q-mb-md">
            <div class="text-h6 col">
              <q-icon name="group" color="primary" class="q-mr-xs" />
              {{ selectedClass?.name }}
              <q-badge color="grey-5" :label="`${selectedEntries.length} disciplinas`" class="q-ml-sm" />
              <q-badge
                v-if="countUnassigned(selectedClassId) > 0"
                color="warning" text-color="dark"
                :label="`${countUnassigned(selectedClassId)} sem professor`"
                class="q-ml-xs"
              />
            </div>
          </div>

          <q-card flat bordered>
            <q-list separator>
              <q-item v-if="!selectedEntries.length" class="q-pa-md">
                <q-item-section>
                  <div class="text-grey-7 text-caption">
                    <q-icon name="info" size="xs" class="q-mr-xs" />
                    Sem disciplinas atribuídas a esta turma. Use <strong>Sincronizar disciplinas</strong> para aplicar o plano curricular.
                  </div>
                </q-item-section>
              </q-item>

              <q-item v-for="entry in selectedEntries" :key="entry.id" class="q-py-sm">
                <q-item-section>
                  <div class="row items-center q-gutter-xs q-mb-sm">
                    <span class="text-weight-medium">{{ entry.subject_name }}</span>
                    <q-badge color="blue-2" text-color="dark" :label="`${entry.hours_per_week}h/sem`" />
                  </div>

                  <div class="row items-center q-gutter-sm flex-wrap">
                    <!-- Current teacher chip (removable) -->
                    <q-chip
                      v-if="entry.teacher_id"
                      dense removable color="positive" text-color="white" icon="person"
                      :label="entry.teacher_name ?? ''"
                      @remove="assignTeacher(entry, null)"
                    />
                    <span v-else class="text-caption text-orange-8">
                      <q-icon name="person_off" size="xs" /> Sem professor
                    </span>

                    <!-- Teacher selector -->
                    <q-select
                      :model-value="null"
                      :options="teacherOptsForSubject(entry.subject_id)"
                      emit-value map-options
                      dense outlined use-input input-debounce="0"
                      @filter="(val, update) => filterTeachersForSubject(val, update, entry.subject_id)"
                      :placeholder="entry.teacher_id ? 'Substituir...' : 'Atribuir professor...'"
                      style="min-width:220px"
                      clearable
                      @update:model-value="(v) => { if (v) assignTeacher(entry, v) }"
                    >
                      <template #prepend><q-icon name="search" size="xs" /></template>
                      <template #option="scope">
                        <q-item v-bind="scope.itemProps">
                          <q-item-section>
                            <q-item-label>{{ scope.opt.name }}</q-item-label>
                          </q-item-section>
                          <q-item-section side>
                            <q-badge
                              :color="scope.opt.remaining < 0 ? 'negative' : scope.opt.remaining === 0 ? 'positive' : scope.opt.remaining <= 2 ? 'warning' : 'blue-3'"
                              :text-color="scope.opt.remaining < 0 ? 'white' : 'dark'"
                              :label="scope.opt.remaining >= 0 ? `+${scope.opt.remaining}h` : `${scope.opt.remaining}h`"
                            />
                          </q-item-section>
                        </q-item>
                      </template>
                      <template #no-option>
                        <q-item>
                          <q-item-section class="text-grey-6 text-caption">Nenhum professor leciona esta disciplina</q-item-section>
                        </q-item>
                      </template>
                    </q-select>
                  </div>
                </q-item-section>

              </q-item>
            </q-list>
          </q-card>
        </template>
      </div>

      <!-- ── Right: teacher hours panel ──────────────────── -->
      <div v-if="showHoursPanel" class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section class="bg-teal-7 text-white q-pa-sm">
            <div class="row items-center">
              <q-icon name="analytics" class="q-mr-xs" />
              <span class="text-subtitle2 col">Saldo de Horas Letivas</span>
              <q-badge color="white" text-color="teal-9" :label="`${teacherHoursPanel.length} docentes`" />
            </div>
          </q-card-section>

          <q-card-section class="q-pa-sm q-pb-xs">
            <q-input v-model="teacherPanelSearch" dense outlined clearable placeholder="Filtrar docente..." class="q-mb-xs">
              <template #prepend><q-icon name="search" size="xs" /></template>
            </q-input>
            <q-btn-toggle
              v-model="teacherPanelFilter"
              dense unelevated no-caps
              :options="[
                { value: 'all', label: 'Todos' },
                { value: 'incomplete', label: 'Incompletos' },
                { value: 'done', label: 'Completos' },
                { value: 'over', label: 'Excedidos' },
              ]"
              color="grey-2" text-color="grey-8"
              toggle-color="teal-7" toggle-text-color="white"
              size="xs"
            />
          </q-card-section>

          <q-separator />

          <q-scroll-area style="height:560px">
            <q-list dense>
              <q-item v-for="t in filteredTeacherHoursPanel" :key="t.id" class="q-py-xs">
                <q-item-section>
                  <div class="row items-center no-wrap q-mb-xs">
                    <span class="text-body2 text-weight-medium col ellipsis" style="max-width:165px">{{ t.name }}</span>
                    <q-badge
                      class="q-ml-xs"
                      :color="t.remaining < 0 ? 'negative' : t.remaining === 0 ? 'positive' : t.remaining <= 2 ? 'warning' : 'blue-3'"
                      :text-color="t.remaining < 0 ? 'white' : 'dark'"
                      :label="t.remaining >= 0 ? `+${t.remaining}h` : `${t.remaining}h`"
                    />
                  </div>
                  <q-linear-progress
                    :value="Math.min(1.15, t.ratio)"
                    :color="t.remaining < 0 ? 'negative' : t.remaining === 0 ? 'positive' : t.remaining <= 2 ? 'warning' : 'teal-5'"
                    track-color="grey-2" size="5px" class="q-mb-xs" style="border-radius:3px"
                  />
                  <div class="text-caption text-grey-6">
                    {{ t.assigned }}h letivo · {{ t.credit }}h crédito · {{ t.component }}h componente
                  </div>
                </q-item-section>
              </q-item>
              <q-item v-if="filteredTeacherHoursPanel.length === 0">
                <q-item-section class="text-grey-5 text-caption q-pa-sm">Sem docentes com este filtro</q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </q-card>
      </div>
    </div>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useClustersStore } from 'stores/clusters'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useTeachersStore } from 'stores/teachers'
import type { Teacher } from 'stores/teachers'
import { useSchoolsStore } from 'stores/schools'
import { useClassesStore } from 'stores/classes'
import type { SchoolClass } from 'stores/classes'

const $q = useQuasar()
const clustersStore = useClustersStore()
const yearsStore = useAcademicYearsStore()
const teachersStore = useTeachersStore()
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

type TeacherOpt = { label: string; name: string; value: number; remaining: number }

// ── State ──────────────────────────────────────────────────────────────────
const loading = ref(false)
const selectedYearId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const classSearch = ref('')
const selectedSchoolIds = reactive(new Set<number>())
const allEntries = ref<Entry[]>([])

// Teacher hours panel
const showHoursPanel = ref(true)
const teacherPanelSearch = ref('')
const teacherPanelFilter = ref<'all' | 'incomplete' | 'done' | 'over'>('all')

// Sync state
const syncing = ref(false)

// Teacher dropdown options cache per subject
const teacherOptsBySubject = ref<Record<number, TeacherOpt[]>>({})

// ── Basic computed ─────────────────────────────────────────────────────────
const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)
const clusterSchools = computed(() => schoolsStore.schools.filter((s) => s.cluster_id === clusterId.value))

const allClasses = computed<SchoolClass[]>(() => {
  const schoolIds = new Set(clusterSchools.value.map((s) => s.id))
  return classesStore.classes.filter(
    (c) => c.academic_year_id === selectedYearId.value && schoolIds.has(c.school_id)
  )
})

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
  const schoolName = (id: number) => schoolsStore.schools.find((s) => s.id === id)?.name ?? '—'
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

const entriesByClassId = computed(() => {
  const map: Record<number, Entry[]> = {}
  for (const e of allEntries.value) {
    if (!map[e.class_id]) map[e.class_id] = []
    map[e.class_id].push(e)
  }
  return map
})

const selectedEntries = computed<Entry[]>(() =>
  (entriesByClassId.value[selectedClassId.value ?? -1] ?? [])
    .slice()
    .sort((a, b) => a.subject_name.localeCompare(b.subject_name))
)

const unassignedCount = computed(() => allEntries.value.filter((e) => !e.teacher_id).length)
function countUnassigned(classId: number) {
  return (entriesByClassId.value[classId] ?? []).filter((e) => !e.teacher_id).length
}

// ── Teacher hours ──────────────────────────────────────────────────────────
const teacherAssignedHours = computed(() => {
  const map: Record<number, number> = {}
  for (const e of allEntries.value) {
    if (e.teacher_id) map[e.teacher_id] = (map[e.teacher_id] ?? 0) + e.hours_per_week
  }
  return map
})

function teacherHoursInfo(t: Teacher) {
  const component = t.teaching_component ?? 22
  const credit = t.credit_hours ?? 0
  const assigned = teacherAssignedHours.value[t.id] ?? 0
  const effective = component - credit
  const remaining = effective - assigned
  const ratio = effective > 0 ? assigned / effective : 0
  return { id: t.id, name: t.name, component, credit, assigned, remaining, ratio }
}

const teacherHoursPanel = computed(() =>
  teachersStore.teachers.map(teacherHoursInfo).sort((a, b) => a.remaining - b.remaining)
)

const filteredTeacherHoursPanel = computed(() => {
  const txt = teacherPanelSearch.value.toLowerCase()
  return teacherHoursPanel.value.filter((t) => {
    if (txt && !t.name.toLowerCase().includes(txt)) return false
    if (teacherPanelFilter.value === 'incomplete' && t.remaining <= 0) return false
    if (teacherPanelFilter.value === 'done' && t.remaining !== 0) return false
    if (teacherPanelFilter.value === 'over' && t.remaining >= 0) return false
    return true
  })
})

// ── Teacher select helpers ─────────────────────────────────────────────────
function makeTeacherOpt(t: Teacher): TeacherOpt {
  return { label: t.name, name: t.name, value: t.id, remaining: teacherHoursInfo(t).remaining }
}

function teacherOptsForSubject(subjectId: number): TeacherOpt[] {
  return (
    teacherOptsBySubject.value[subjectId] ??
    teachersStore.teachers
      .filter((t) => t.subject_ids?.includes(subjectId))
      .map(makeTeacherOpt)
      .sort((a, b) => b.remaining - a.remaining)
  )
}

function filterTeachersForSubject(val: string, update: (fn: () => void) => void, subjectId: number) {
  update(() => {
    const txt = val.toLowerCase()
    const opts = teachersStore.teachers
      .filter((t) => t.subject_ids?.includes(subjectId) && (!txt || t.name.toLowerCase().includes(txt)))
      .map(makeTeacherOpt)
      .sort((a, b) => b.remaining - a.remaining)
    teacherOptsBySubject.value = { ...teacherOptsBySubject.value, [subjectId]: opts }
  })
}

// ── Actions ────────────────────────────────────────────────────────────────
function toggleSchool(id: number) {
  if (selectedSchoolIds.has(id)) selectedSchoolIds.delete(id)
  else selectedSchoolIds.add(id)
}

function selectClass(classId: number) {
  selectedClassId.value = classId
  teacherOptsBySubject.value = {}
}

async function load() {
  if (!selectedYearId.value || !clusterId.value) return
  loading.value = true
  selectedClassId.value = null
  allEntries.value = []
  try {
    await classesStore.fetchAll({ academic_year_id: selectedYearId.value })
    const { data } = await api.get<any[]>('/classes/curriculum-overview', {
      params: { cluster_id: clusterId.value, academic_year_id: selectedYearId.value },
    })
    allEntries.value = data.map((e) => ({
      id: e.id,
      class_id: e.class_id,
      subject_id: e.subject_id,
      subject_name: e.subject_name ?? `ID:${e.subject_id}`,
      hours_per_week: e.hours_per_week,
      teacher_id: e.teacher_id ?? null,
      teacher_name: e.teacher_name ?? null,
    }))
  } catch {
    // silently keep entries empty on load failure
  } finally {
    loading.value = false
  }
}

async function assignTeacher(entry: Entry, teacherId: number | null) {
  const prevId = entry.teacher_id
  const prevName = entry.teacher_name
  entry.teacher_id = teacherId
  entry.teacher_name = teachersStore.teachers.find((t) => t.id === teacherId)?.name ?? null
  teacherOptsBySubject.value = {}
  try {
    await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: teacherId })
    $q.notify({ type: teacherId ? 'positive' : 'info', message: teacherId ? 'Professor atribuído' : 'Professor removido', timeout: 1200 })
  } catch {
    entry.teacher_id = prevId
    entry.teacher_name = prevName
    teacherOptsBySubject.value = {}
    $q.notify({ type: 'negative', message: 'Erro ao guardar' })
  }
}

async function syncFromPlans() {
  if (!clusterId.value || !selectedYearId.value) return
  syncing.value = true
  let ok = false
  try {
    const res = await api.post('/curriculum-plans/apply', {
      cluster_id: clusterId.value,
      academic_year_id: selectedYearId.value,
      overwrite: false,
    })
    ok = true
    const msg = typeof res.data?.message === 'string' ? res.data.message : 'Disciplinas sincronizadas'
    $q.notify({ type: 'positive', message: msg })
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    const status = e?.response?.status as number | undefined
    let msg: string
    if (typeof detail === 'string') {
      msg = detail
    } else if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0]
      const field = Array.isArray(first?.loc) ? (first.loc as string[]).slice(1).join('.') : ''
      const errMsg = typeof first?.msg === 'string' ? first.msg : 'Erro de validação'
      msg = field ? `${field}: ${errMsg}` : errMsg
    } else {
      msg = status ? `Erro ${status} ao sincronizar disciplinas` : 'Erro ao sincronizar disciplinas'
    }
    $q.notify({ type: 'negative', message: msg })
  } finally {
    syncing.value = false
  }
  if (ok) await load()
}

onMounted(async () => {
  await Promise.all([
    clustersStore.fetchAll(),
    yearsStore.fetchAll(),
    teachersStore.fetchAll(),
    schoolsStore.fetchAll(),
  ])
  selectedYearId.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  if (selectedYearId.value) await load()
})
</script>
