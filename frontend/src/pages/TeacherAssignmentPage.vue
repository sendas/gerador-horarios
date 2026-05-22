<template>
  <q-page padding>
    <!-- Header -->
    <div class="row items-center q-mb-sm q-gutter-sm flex-wrap">
      <div class="text-h5 col">Atribuição de Professores</div>
      <q-chip v-if="unassignedCount > 0" color="warning" text-color="dark" icon="warning" :label="`${unassignedCount} sem professor`" />
      <q-chip v-else-if="allEntries.length > 0" color="positive" text-color="white" icon="check_circle" label="Todos atribuídos" />

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
            <q-item-section><q-item-label>Por ano de escolaridade...</q-item-label></q-item-section>
          </q-item>
          <q-separator />
          <q-item clickable v-close-popup @click="startAutoFill([...selectedClassIds])" :disable="selectedClassIds.size === 0">
            <q-item-section avatar><q-icon name="checklist" color="teal" /></q-item-section>
            <q-item-section>
              <q-item-label>Preencher selecionados</q-item-label>
              <q-item-label caption>{{ selectedClassIds.size }} turma(s)</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>

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
              <q-item-label caption>{{ selectedClassIds.size }} turma(s)</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>

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
        <div class="row items-center q-mb-xs q-gutter-xs">
          <q-btn flat dense size="xs" icon="select_all" label="Selec. todos" color="teal" @click="selectAllVisible" />
          <q-btn v-if="selectedClassIds.size > 0" flat dense size="xs" icon="deselect" label="Limpar sel." color="grey-6" @click="selectedClassIds.clear()" />
          <q-space />
          <q-badge v-if="selectedClassIds.size > 0" color="teal" :label="`${selectedClassIds.size} sel.`" />
        </div>
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
              <q-item-section avatar style="min-width:32px">
                <q-checkbox :model-value="selectedClassIds.has(cls.id)" dense size="sm" color="teal"
                  @click.stop @update:model-value="toggleClassSelection(cls.id)" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ cls.name }}</q-item-label>
                <q-item-label caption>{{ cls.year_level }}.º ano</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge v-if="countUnassigned(cls.id) > 0" color="warning" text-color="dark" :label="countUnassigned(cls.id)" />
                <q-badge v-else-if="(entriesByClassId[cls.id]?.length ?? 0) > 0" color="positive" icon="check" label="" />
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
              <q-item v-if="!selectedEntries.length" class="text-grey-5 text-caption">
                <q-item-section>Sem disciplinas. Adicione disciplinas com o botão acima.</q-item-section>
              </q-item>
              <q-item v-for="entry in selectedEntries" :key="entry.id" class="q-py-sm">
                <q-item-section>
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <span class="text-weight-medium">{{ entry.subject_name }}</span>
                    <q-badge color="blue-2" text-color="dark" :label="`${entry.hours_per_week}h/sem`" />
                  </div>
                  <div class="row items-center q-gutter-sm flex-wrap">
                    <q-chip
                      v-if="entry.teacher_id"
                      dense removable color="positive" text-color="white" icon="person"
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
                      dense outlined use-input input-debounce="0"
                      @filter="(val, update) => filterTeachersForSubject(val, update, entry.subject_id)"
                      :placeholder="entry.teacher_id ? 'Substituir...' : 'Atribuir professor...'"
                      style="min-width:210px"
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
          <q-scroll-area style="height:540px">
            <q-list dense>
              <q-item
                v-for="t in filteredTeacherHoursPanel"
                :key="t.id"
                class="q-py-xs"
              >
                <q-item-section>
                  <div class="row items-center no-wrap q-mb-xs">
                    <span class="text-body2 text-weight-medium col ellipsis" style="max-width:160px">{{ t.name }}</span>
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
            emit-value map-options dense outlined use-input input-debounce="0"
            @filter="filterSubjectsFn"
            class="q-mb-sm"
          />
          <q-input v-model.number="newHours" label="Horas/semana *" type="number" min="1" max="10" dense outlined class="q-mb-sm" />
          <q-select
            v-model="newTeacherId"
            :options="filteredTeacherOpts"
            label="Professor (opcional)"
            emit-value map-options dense outlined clearable use-input input-debounce="0"
            @filter="filterAllTeachersFn"
          >
            <template #option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>{{ scope.opt.name }}</q-item-section>
                <q-item-section side>
                  <q-badge
                    :color="scope.opt.remaining < 0 ? 'negative' : scope.opt.remaining === 0 ? 'positive' : scope.opt.remaining <= 2 ? 'warning' : 'blue-3'"
                    :text-color="scope.opt.remaining < 0 ? 'white' : 'dark'"
                    :label="scope.opt.remaining >= 0 ? `+${scope.opt.remaining}h` : `${scope.opt.remaining}h`"
                  />
                </q-item-section>
              </q-item>
            </template>
          </q-select>
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
          <div class="text-caption text-grey-7 q-mb-sm">Selecione os anos de escolaridade:</div>
          <div class="row q-gutter-sm flex-wrap">
            <q-chip
              v-for="yl in availableYearLevels" :key="yl"
              clickable dense square
              :color="fillYearLevels.has(yl) ? 'teal' : 'grey-3'"
              :text-color="fillYearLevels.has(yl) ? 'white' : 'dark'"
              :icon="fillYearLevels.has(yl) ? 'check' : 'radio_button_unchecked'"
              @click="toggleFillYear(yl)"
            >{{ yl }}.º ano</q-chip>
          </div>
          <div class="text-caption text-grey-6 q-mt-sm">
            <q-icon name="info" size="xs" class="q-mr-xs" />Só preenche entradas sem professor.
          </div>
        </q-card-section>
        <q-card-section class="row justify-end q-gutter-sm">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn color="teal" icon="auto_fix_high" label="Preencher"
            :disable="fillYearLevels.size === 0" :loading="bulkRunning"
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
import type { Teacher } from 'stores/teachers'
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

type TeacherOpt = { label: string; name: string; value: number; remaining: number }

// ── State ──────────────────────────────────────────────────────────────────
const loading = ref(false)
const bulkRunning = ref(false)
const selectedYearId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const classSearch = ref('')
const selectedSchoolIds = reactive(new Set<number>())
const selectedClassIds = reactive(new Set<number>())
const allEntries = ref<Entry[]>([])

// Teacher hours panel
const showHoursPanel = ref(true)
const teacherPanelSearch = ref('')
const teacherPanelFilter = ref<'all' | 'incomplete' | 'done' | 'over'>('all')

// Year-level fill dialog
const showYearFillDialog = ref(false)
const fillYearLevels = reactive(new Set<number>())

// Add subject dialog
const showAddSubject = ref(false)
const newSubjectId = ref<number | null>(null)
const newHours = ref(2)
const newTeacherId = ref<number | null>(null)
const teacherOptsBySubject = ref<Record<number, TeacherOpt[]>>({})
const filteredTeacherOpts = ref<TeacherOpt[]>([])
const availableSubjectOptions = ref<{ label: string; value: number }[]>([])

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
  teachersStore.teachers
    .map(teacherHoursInfo)
    .sort((a, b) => a.remaining - b.remaining)
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
  const info = teacherHoursInfo(t)
  return { label: t.name, name: t.name, value: t.id, remaining: info.remaining }
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

function filterAllTeachersFn(val: string, update: (fn: () => void) => void) {
  update(() => {
    const txt = val.toLowerCase()
    filteredTeacherOpts.value = teachersStore.teachers
      .filter((t) => !txt || t.name.toLowerCase().includes(txt))
      .map(makeTeacherOpt)
      .sort((a, b) => b.remaining - a.remaining)
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
      subject_name: e.subject_name ?? subjectsStore.subjects.find((s) => s.id === e.subject_id)?.name ?? `ID:${e.subject_id}`,
      hours_per_week: e.hours_per_week,
      teacher_id: e.teacher_id ?? null,
      teacher_name: e.teacher_name ?? null,
    }))
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

async function deleteEntry(entry: Entry) {
  $q.dialog({
    title: 'Remover disciplina',
    message: `Remover "${entry.subject_name}" da turma?`,
    ok: { label: 'Remover', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    try {
      await api.delete(`/classes/curriculum/${entry.id}`)
      allEntries.value = allEntries.value.filter((e) => e.id !== entry.id)
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
  filteredTeacherOpts.value = teachersStore.teachers.map(makeTeacherOpt).sort((a, b) => b.remaining - a.remaining)
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
    allEntries.value = [...allEntries.value, {
      id: data.id,
      class_id: selectedClassId.value!,
      subject_id: newSubjectId.value!,
      subject_name: subj?.name ?? '',
      hours_per_week: newHours.value,
      teacher_id: newTeacherId.value ?? null,
      teacher_name: teacher?.name ?? null,
    }]
    showAddSubject.value = false
    $q.notify({ type: 'positive', message: 'Disciplina adicionada' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao adicionar disciplina' })
  }
}

// ── Bulk ops ───────────────────────────────────────────────────────────────
const availableYearLevels = computed(() =>
  [...new Set(allClasses.value.map((c) => c.year_level))].sort((a, b) => a - b)
)

function getVisibleClassIds() {
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

async function startAutoFill(classIds: number[]) {
  if (!classIds.length) return
  bulkRunning.value = true
  let filled = 0; let skipped = 0
  try {
    for (const classId of classIds) {
      for (const entry of (entriesByClassId.value[classId] ?? [])) {
        if (entry.teacher_id) continue
        const candidates = teachersStore.teachers
          .filter((t) => t.subject_ids?.includes(entry.subject_id))
          .sort((a, b) => teacherHoursInfo(b).remaining - teacherHoursInfo(a).remaining)
        if (!candidates.length) { skipped++; continue }
        try {
          await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: candidates[0].id })
          entry.teacher_id = candidates[0].id
          entry.teacher_name = candidates[0].name
          filled++
        } catch { /* skip */ }
      }
    }
    $q.notify({ type: 'positive', message: `${filled} atribuição(ões) preenchida(s)${skipped ? `, ${skipped} sem professor disponível` : ''}` })
  } finally {
    bulkRunning.value = false
  }
}

async function startAutoFillByYear() {
  const ids = allClasses.value.filter((c) => fillYearLevels.has(c.year_level)).map((c) => c.id)
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
      for (const entry of (entriesByClassId.value[classId] ?? [])) {
        if (!entry.teacher_id) continue
        try {
          await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: null })
          entry.teacher_id = null
          entry.teacher_name = null
          cleared++
        } catch { /* skip */ }
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
  selectedYearId.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  if (selectedYearId.value) await load()
})
</script>
