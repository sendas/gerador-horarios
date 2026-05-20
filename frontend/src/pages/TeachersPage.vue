<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Professores</div>
      <q-btn color="primary" icon="add" label="Novo" @click="openCreate" />
      <q-btn color="secondary" icon="upload" label="Importar" @click="showImport = true" class="q-ml-sm" />
    </div>

    <ImportDialog
      v-model="showImport"
      title="Importar Professores"
      endpoint="/imports/teachers"
      :extra-params="{ cluster_id: selectedClusterId }"
      entity-type="teachers"
      @done="teachersStore.fetchAll()"
    />

    <!-- School filter -->
    <div class="row items-center q-mb-sm q-gutter-xs">
      <span class="text-caption text-grey-7 q-mr-xs">Filtrar por escola:</span>
      <q-chip
        v-for="school in schoolsStore.schools"
        :key="school.id"
        clickable
        :color="selectedSchoolIds.has(school.id) ? 'teal-7' : 'grey-3'"
        :text-color="selectedSchoolIds.has(school.id) ? 'white' : 'dark'"
        :icon="selectedSchoolIds.has(school.id) ? 'check' : undefined"
        :label="school.name"
        @click="toggleSchoolFilter(school.id)"
      />
      <q-btn v-if="selectedSchoolIds.size > 0" flat dense size="sm" icon="close" color="grey-6" label="Limpar" @click="selectedSchoolIds.clear()" />
      <q-badge v-if="selectedSchoolIds.size > 0" color="teal-7" :label="`${filteredTeachers.length} professor(es)`" class="q-ml-xs" />
    </div>

    <q-table :rows="filteredTeachers" :columns="columns" row-key="id" :loading="teachersStore.loading">
      <template #body-cell-subject_names="props">
        <q-td :props="props">
          <q-chip v-for="s in props.row.subject_names" :key="s" size="sm" :label="s" color="blue-2" text-color="dark" class="q-mr-xs" />
          <span v-if="!props.row.subject_names?.length" class="text-grey-5">—</span>
        </q-td>
      </template>
      <template #body-cell-preferred_free_day="props">
        <q-td :props="props">{{ props.row.preferred_free_day !== null && props.row.preferred_free_day !== undefined ? DAYS[props.row.preferred_free_day] : '—' }}</q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn unelevated size="sm" color="info" icon="school" label="Escolas" @click="openSchools(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="secondary" icon="book" label="Disciplinas" @click="openSubjects(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="teal" icon="groups" label="Turmas" @click="openCurriculum(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="positive" icon="event_available" label="Disponibilidade" @click="openAvailability(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openEdit(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Teacher dialog -->
    <q-dialog v-model="dialog">
      <q-card style="min-width: 450px">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ editing ? 'Editar' : 'Novo' }} Professor</div>
          <q-space /><q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-form @submit.prevent="save" greedy>
            <q-select v-if="!editing" v-model="form.cluster_id" :options="clusterOptions" label="Agrupamento *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" class="q-mb-sm" />
            <q-input v-model="form.name" label="Nome *" :rules="[v => !!v || 'Obrigatório']" class="q-mb-sm" />
            <q-input v-model="form.email" label="Email" type="email" />
            <q-input v-model.number="form.max_daily_lessons" label="Máx aulas/dia" type="number" min="1" max="10" />
            <q-select
              v-model="form.preferred_free_day"
              :options="dayOptions"
              label="Dia livre preferido"
              emit-value map-options clearable
            />
            <q-separator class="q-my-sm" />
            <div class="text-caption text-grey-6 q-mb-sm">Preferências de horário</div>

            <div class="row q-gutter-sm">
              <q-input
                v-model.number="form.min_start_slot"
                label="Não entrar antes do tempo n.°"
                type="number"
                min="1"
                :max="10"
                hint="Ex: 2 = não começa no 1.° tempo"
                style="min-width: 200px"
                clearable
              />
              <q-input
                v-model.number="form.max_end_slot"
                label="Não sair depois do tempo n.°"
                type="number"
                min="1"
                :max="10"
                hint="Ex: 6 = termina no máximo no 6.° tempo"
                style="min-width: 200px"
                clearable
              />
            </div>
            <q-select
              v-model="form.preferred_shift"
              :options="shiftOptions"
              label="Turno preferido"
              emit-value
              map-options
              clearable
            />
            <q-input
              v-model.number="form.max_consecutive_lessons"
              label="Máx. aulas consecutivas (sobrepõe-se à regra global)"
              type="number"
              min="1"
              :max="8"
              clearable
              hint="Deixa vazio para usar a regra global"
            />
            <q-separator class="q-my-sm" />
            <div class="text-caption text-grey-6 q-mb-sm">Componente letiva</div>
            <q-input
              v-model.number="form.teaching_component"
              label="Horas letivas/semana"
              type="number"
              min="14"
              max="22"
              clearable
              hint="Entre 14 e 22 horas letivas por semana"
            />
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" :label="editing ? 'Guardar' : 'Criar'" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Schools dialog -->
    <q-dialog v-model="schoolsDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="row items-center">
          <div class="text-h6">Escolas: {{ selectedTeacher?.name }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-list>
            <q-item v-for="a in schoolAssignments" :key="a.id">
              <q-item-section>{{ schoolName(a.school_id) }} (Ano: {{ yearName(a.academic_year_id) }})</q-item-section>
              <q-item-section side>{{ a.travel_time_minutes }} min viagem</q-item-section>
              <q-item-section side>
                <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="removeSchoolAssignment(a.id)" />
              </q-item-section>
            </q-item>
          </q-list>
          <q-separator class="q-my-md" />
          <div class="text-subtitle2 q-mb-sm">Adicionar escola</div>
          <div class="row q-col-gutter-sm items-end">
            <div class="col-4">
              <q-select v-model="newAssignment.school_id" :options="schoolOptions" label="Escola" emit-value map-options dense />
            </div>
            <div class="col-4">
              <q-select v-model="newAssignment.academic_year_id" :options="yearOptions" label="Ano Letivo" emit-value map-options dense />
            </div>
            <div class="col-3">
              <q-input v-model.number="newAssignment.travel_time_minutes" label="Viagem (min)" type="number" dense />
            </div>
            <div class="col-1">
              <q-btn round color="primary" icon="add" dense @click="addSchoolAssignment" />
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Subjects dialog -->
    <q-dialog v-model="subjectsDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="row items-center">
          <div class="text-h6">Disciplinas: {{ selectedTeacher?.name }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-xs q-mb-md">
            <q-chip
              v-for="s in teacherSubjects"
              :key="s.subject_id"
              removable
              @remove="removeSubject(s.subject_id)"
              :label="subjectName(s.subject_id)"
              color="primary"
              text-color="white"
            />
          </div>
          <div class="row q-col-gutter-sm items-center">
            <div class="col">
              <q-select v-model="newSubjectId" :options="availableSubjectOptions" label="Adicionar disciplina" emit-value map-options dense />
            </div>
            <div>
              <q-btn round color="primary" icon="add" @click="addSubject" :disable="!newSubjectId" />
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Curriculum / class assignment dialog -->
    <q-dialog v-model="curriculumDialog" full-width>
      <q-card style="max-width:960px;width:100%">
        <q-card-section class="row items-center q-pb-sm">
          <div class="text-h6 row items-center q-gutter-sm">
            <span>
              <q-icon name="groups" color="teal" class="q-mr-xs" />
              Turmas de {{ selectedTeacher?.name }}
            </span>
            <q-chip
              v-if="teachingComponent"
              dense square
              :color="assignedHours > teachingComponent ? 'negative' : assignedHours === teachingComponent ? 'positive' : 'blue-grey-6'"
              text-color="white"
              icon="schedule"
            >
              {{ assignedHours }}h / {{ teachingComponent }}h
              <q-tooltip>Horas letivas atribuídas / componente letiva total</q-tooltip>
            </q-chip>
            <q-chip v-else-if="assignedHours > 0" dense square color="blue-grey-6" text-color="white" icon="schedule">
              {{ assignedHours }}h atribuídas
            </q-chip>
          </div>
          <q-space />
          <q-select
            v-model="curriculumYear"
            :options="yearOptions"
            label="Ano Letivo"
            emit-value map-options dense outlined
            style="min-width:160px"
            @update:model-value="loadCurriculum"
            class="q-mr-md"
          />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <!-- No subjects warning -->
        <q-card-section v-if="!selectedTeacher?.subject_ids?.length" class="text-center q-py-xl">
          <q-icon name="warning" color="warning" size="48px" />
          <div class="q-mt-sm text-subtitle1">Este professor não tem disciplinas configuradas.</div>
          <div class="text-caption text-grey-6 q-mb-md">Adicione primeiro as disciplinas que o professor leciona.</div>
          <q-btn color="secondary" icon="book" label="Gerir disciplinas" unelevated @click="curriculumDialog=false; openSubjects(selectedTeacher!)" />
        </q-card-section>

        <template v-else-if="curriculumYear">
          <!-- Subject selector + defaults -->
          <q-card-section class="q-pt-sm q-pb-xs">
            <div class="row items-center q-gutter-xs q-mb-sm flex-wrap">
              <span class="text-caption text-grey-7">Disciplina:</span>
              <q-chip
                v-for="subId in selectedTeacher!.subject_ids"
                :key="subId"
                clickable dense
                :color="curriculumSubjectId === subId ? 'teal' : 'grey-3'"
                :text-color="curriculumSubjectId === subId ? 'white' : 'dark'"
                @click="curriculumSubjectId = subId"
              >{{ subjectName(subId) }}</q-chip>
            </div>

            <div class="row items-center q-gutter-md">
              <q-input
                v-model.number="defaultHours"
                label="Horas/semana (novas entradas)"
                type="number" min="1" max="20"
                dense outlined style="max-width:240px"
              />
              <q-chip icon="check_circle" color="teal" text-color="white" :label="`${assignedClassCount} turmas atribuídas`" dense />
              <q-space />
              <q-btn flat dense size="sm" color="teal" icon="done_all" label="Atribuir todas" @click="assignAllClasses" />
              <q-btn flat dense size="sm" color="grey" icon="remove_done" label="Remover todas" @click="removeAllClasses" class="q-ml-xs" />
            </div>
          </q-card-section>

          <q-separator />

          <q-card-section class="q-pt-sm" style="max-height:60vh;overflow-y:auto">
            <q-input v-model="curriculumClassSearch" dense outlined clearable placeholder="Pesquisar turma..." class="q-mb-sm">
              <template #prepend><q-icon name="search" /></template>
            </q-input>

            <div v-if="curriculumLoading" class="text-center q-py-xl">
              <q-spinner color="teal" size="40px" />
            </div>

            <div v-else-if="curriculumClassGroups.length === 0" class="text-grey-6 text-caption text-center q-py-xl">
              Sem turmas para este ano letivo
            </div>

            <div v-for="group in curriculumClassGroups" :key="group.school_id" class="q-mb-lg">
              <div class="row items-center q-mb-sm">
                <q-icon name="school" color="grey-5" size="sm" class="q-mr-xs" />
                <span class="text-subtitle2 text-grey-8">{{ group.school_name }}</span>
                <q-badge
                  :color="group.assignedCount === group.classes.length ? 'positive' : group.assignedCount > 0 ? 'warning' : 'grey-4'"
                  :text-color="group.assignedCount === group.classes.length ? 'white' : 'dark'"
                  :label="`${group.assignedCount}/${group.classes.length}`"
                  class="q-ml-sm"
                />
                <q-space />
                <q-btn flat dense size="xs" color="teal" label="Todas" @click="assignSchoolClasses(group.classes)" />
              </div>

              <div class="row q-gutter-sm">
                <q-card
                  v-for="cls in group.classes"
                  :key="cls.id"
                  flat bordered
                  clickable
                  :class="isClassAssigned(cls.id) ? 'bg-teal-1 border-teal' : ''"
                  style="min-width:110px;max-width:130px"
                  @click="toggleClass(cls)"
                >
                  <q-card-section class="q-pa-sm text-center">
                    <q-checkbox
                      :model-value="isClassAssigned(cls.id)"
                      color="teal" dense
                      @click.stop
                      @update:model-value="(v) => toggleClass(cls, v)"
                    />
                    <div class="text-weight-medium q-mt-xs">{{ cls.name }}</div>
                    <div class="text-caption text-grey-6">{{ cls.year_level }}.º ano</div>
                    <q-badge
                      v-if="getClassOtherTeacher(cls.id)"
                      color="orange-2" text-color="dark"
                      :label="getClassOtherTeacher(cls.id)!"
                      class="q-mt-xs"
                      style="max-width:110px;white-space:normal;word-break:break-word"
                    />
                  </q-card-section>
                </q-card>
              </div>
            </div>
          </q-card-section>
        </template>

        <q-card-section v-else class="text-grey text-center q-py-xl">
          Selecione um ano letivo
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Availability dialog -->
    <q-dialog v-model="availabilityDialog" full-width>
      <q-card>
        <q-card-section class="row items-center">
          <div class="text-h6">Disponibilidade: {{ selectedTeacher?.name }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-select v-model="availYear" :options="yearOptions" label="Ano Letivo" emit-value map-options class="q-mb-md" style="max-width:200px" @update:model-value="loadAvailability" />
          <div class="timetable-grid" v-if="availYear">
            <table style="border-collapse:collapse;width:100%">
              <thead>
                <tr>
                  <th style="padding:4px 8px;border:1px solid #ddd;background:#2c3e50;color:white">Tempo</th>
                  <th v-for="day in DAYS" :key="day" style="padding:4px 8px;border:1px solid #ddd;background:#2c3e50;color:white">{{ day }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="slot in uniqueSlots" :key="slot">
                  <td style="padding:4px 8px;border:1px solid #ddd;text-align:center;font-weight:bold">{{ slot }}</td>
                  <td v-for="(day, dayIdx) in DAYS" :key="dayIdx" style="padding:4px;border:1px solid #ddd;text-align:center">
                    <q-checkbox
                      :model-value="isAvailable(dayIdx, slot)"
                      @update:model-value="toggleAvailability(dayIdx, slot)"
                      color="positive"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="row justify-end q-mt-md">
              <q-btn color="primary" label="Guardar disponibilidade" @click="saveAvailability" />
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useTeachersStore, type Teacher } from 'stores/teachers'
import { useClustersStore } from 'stores/clusters'
import { useSchoolsStore } from 'stores/schools'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useSubjectsStore } from 'stores/subjects'
import { useClassesStore, type SchoolClass } from 'stores/classes'
import { api } from 'boot/axios'
import ImportDialog from 'components/ImportDialog.vue'

const $q = useQuasar()
const teachersStore = useTeachersStore()
const clustersStore = useClustersStore()
const classesStore = useClassesStore()

const showImport = ref(false)
const selectedClusterId = computed(() => clustersStore.clusters[0]?.id ?? null)
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()
const subjectsStore = useSubjectsStore()

const DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'email', label: 'Email', field: 'email', align: 'left' as const },
  { name: 'subject_names', label: 'Disciplinas', field: 'subject_names', align: 'left' as const },
  { name: 'teaching_component', label: 'Comp. Letiva', field: 'teaching_component', align: 'center' as const },
  { name: 'max_daily_lessons', label: 'Máx/dia', field: 'max_daily_lessons', align: 'center' as const },
  { name: 'preferred_free_day', label: 'Dia livre', field: 'preferred_free_day', align: 'center' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const dayOptions = DAYS.map((d, i) => ({ label: d, value: i }))
const shiftOptions = [
  { label: 'Manhã (preferência)', value: 'morning' },
  { label: 'Tarde (preferência)', value: 'afternoon' },
]
const dialog = ref(false)
const editing = ref<null | Teacher>(null)
const form = ref({
  cluster_id: null as number | null,
  name: '',
  email: '',
  max_daily_lessons: 5,
  preferred_free_day: null as number | null,
  min_start_slot: null as number | null,
  max_end_slot: null as number | null,
  preferred_shift: null as string | null,
  max_consecutive_lessons: null as number | null,
  teaching_component: null as number | null,
})

// School filter
const selectedSchoolIds = reactive(new Set<number>())
function toggleSchoolFilter(id: number) {
  if (selectedSchoolIds.has(id)) selectedSchoolIds.delete(id)
  else selectedSchoolIds.add(id)
}
const filteredTeachers = computed(() => {
  if (selectedSchoolIds.size === 0) return teachersStore.teachers
  return teachersStore.teachers.filter((t) =>
    (t.school_ids ?? []).some((sid) => selectedSchoolIds.has(sid))
  )
})

const clusterOptions = computed(() => clustersStore.clusters.map((c) => ({ label: c.name, value: c.id })))
const schoolOptions = computed(() => schoolsStore.schools.map((s) => ({ label: s.name, value: s.id })))
const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))

// Schools
const schoolsDialog = ref(false)
const selectedTeacher = ref<Teacher | null>(null)
const schoolAssignments = ref<{ id: number; school_id: number; academic_year_id: number; travel_time_minutes: number }[]>([])
const newAssignment = ref({ school_id: null as number | null, academic_year_id: null as number | null, travel_time_minutes: 0 })

function schoolName(id: number) { return schoolsStore.schools.find((s) => s.id === id)?.name ?? '—' }
function yearName(id: number) { return yearsStore.years.find((y) => y.id === id)?.name ?? '—' }

// Subjects
const subjectsDialog = ref(false)
const teacherSubjects = ref<{ id: number; teacher_id: number; subject_id: number }[]>([])
const newSubjectId = ref<number | null>(null)

function subjectName(id: number) { return subjectsStore.subjects.find((s) => s.id === id)?.name ?? '—' }
const availableSubjectOptions = computed(() => {
  const assigned = new Set(teacherSubjects.value.map((ts) => ts.subject_id))
  return subjectsStore.subjects.filter((s) => !assigned.has(s.id)).map((s) => ({ label: s.name, value: s.id }))
})

// Curriculum assignment
type CurriculumEntry = {
  id: number
  class_id: number
  class_name: string
  year_level: number
  school_id: number | null
  subject_id: number
  subject_name: string
  hours_per_week: number
  teacher_id: number | null
  teacher_name: string | null
}

const curriculumDialog = ref(false)
const curriculumLoading = ref(false)
const curriculumYear = ref<number | null>(null)
const curriculumSubjectId = ref<number | null>(null)
const defaultHours = ref(2)
const curriculumClassSearch = ref('')
// All curriculum entries for the cluster+year (to detect existing entries per class+subject)
const allClusterEntries = ref<CurriculumEntry[]>([])

const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)

// All classes in the cluster for the curriculum year
const curriculumAllClasses = computed<SchoolClass[]>(() => {
  const schoolIds = new Set(schoolsStore.schools.filter((s) => s.cluster_id === clusterId.value).map((s) => s.id))
  return classesStore.classes.filter(
    (c) => c.academic_year_id === curriculumYear.value && schoolIds.has(c.school_id)
  )
})

// Map class_id → CurriculumEntry for the selected subject (quick lookup)
const classEntryMap = computed(() => {
  const map = new Map<number, CurriculumEntry>()
  if (!curriculumSubjectId.value) return map
  for (const e of allClusterEntries.value) {
    if (e.subject_id === curriculumSubjectId.value) map.set(e.class_id, e)
  }
  return map
})

function isClassAssigned(classId: number): boolean {
  const e = classEntryMap.value.get(classId)
  return !!(e && e.teacher_id === selectedTeacher.value?.id)
}

function getClassOtherTeacher(classId: number): string | null {
  const e = classEntryMap.value.get(classId)
  if (!e || !e.teacher_id || e.teacher_id === selectedTeacher.value?.id) return null
  return teacherName(e.teacher_id)
}

// Classes grouped by school with search filter + assigned counts
const curriculumClassGroups = computed(() => {
  const txt = curriculumClassSearch.value.toLowerCase()
  const filtered = curriculumAllClasses.value.filter(
    (c) => !txt || c.name.toLowerCase().includes(txt) || String(c.year_level).includes(txt)
  )
  const bySchool = new Map<number, SchoolClass[]>()
  for (const c of filtered) {
    if (!bySchool.has(c.school_id)) bySchool.set(c.school_id, [])
    bySchool.get(c.school_id)!.push(c)
  }
  return [...bySchool.entries()]
    .map(([schoolId, classes]) => ({
      school_id: schoolId,
      school_name: schoolsStore.schools.find((s) => s.id === schoolId)?.name ?? '—',
      classes: classes.sort((a, b) => a.year_level - b.year_level || a.name.localeCompare(b.name)),
      assignedCount: classes.filter((c) => isClassAssigned(c.id)).length,
    }))
    .sort((a, b) => a.school_name.localeCompare(b.school_name))
})

const assignedClassCount = computed(() =>
  curriculumAllClasses.value.filter((c) => isClassAssigned(c.id)).length
)

// Total hours assigned to this teacher across all subjects this year
const assignedHours = computed(() => {
  if (!selectedTeacher.value) return 0
  return allClusterEntries.value
    .filter((e) => e.teacher_id === selectedTeacher.value!.id)
    .reduce((sum, e) => sum + (e.hours_per_week ?? 0), 0)
})

const teachingComponent = computed(() => selectedTeacher.value?.teaching_component ?? null)

function teacherName(id: number | null) {
  if (!id) return ''
  return teachersStore.teachers.find((t) => t.id === id)?.name ?? '?'
}

async function openCurriculum(teacher: Teacher) {
  selectedTeacher.value = teacher
  curriculumYear.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  curriculumSubjectId.value = teacher.subject_ids?.[0] ?? null
  curriculumClassSearch.value = ''
  curriculumDialog.value = true
  if (curriculumYear.value) await loadCurriculum()
}

async function loadCurriculum() {
  if (!clusterId.value || !curriculumYear.value) return
  curriculumLoading.value = true
  try {
    const [entriesRes] = await Promise.all([
      api.get<CurriculumEntry[]>('/classes/curriculum-overview', {
        params: { cluster_id: clusterId.value, academic_year_id: curriculumYear.value },
      }),
      classesStore.fetchAll({ academic_year_id: curriculumYear.value }),
    ])
    allClusterEntries.value = entriesRes.data
  } finally {
    curriculumLoading.value = false
  }
}

async function toggleClass(cls: SchoolClass, forceAssign?: boolean) {
  if (!curriculumSubjectId.value || !selectedTeacher.value) return
  const shouldAssign = forceAssign !== undefined ? forceAssign : !isClassAssigned(cls.id)
  const existing = classEntryMap.value.get(cls.id)

  if (shouldAssign) {
    if (existing) {
      if (existing.teacher_id && existing.teacher_id !== selectedTeacher.value.id) {
        $q.dialog({
          title: 'Substituir professor',
          message: `${cls.name} já tem "${teacherName(existing.teacher_id)}" atribuído. Substituir?`,
          ok: { label: 'Substituir', color: 'warning' }, cancel: true,
        }).onOk(() => doUpdateEntry(existing, selectedTeacher.value!.id))
        return
      }
      await doUpdateEntry(existing, selectedTeacher.value.id)
    } else {
      await doCreateEntry(cls)
    }
  } else {
    if (existing && existing.teacher_id === selectedTeacher.value.id) {
      await doUpdateEntry(existing, null)
    }
  }
}

async function doUpdateEntry(entry: CurriculumEntry, teacherId: number | null) {
  try {
    await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: teacherId })
    entry.teacher_id = teacherId
    entry.teacher_name = teacherId ? teacherName(teacherId) : null
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: unknown } } }
    const status = err?.response?.status ?? '?'
    const detail = err?.response?.data?.detail
    const msg = detail ? (typeof detail === 'string' ? detail : JSON.stringify(detail)) : 'Sem detalhe'
    console.error('[doUpdateEntry] HTTP', status, detail)
    $q.notify({ type: 'negative', message: `Erro ${status} ao atualizar entrada`, caption: msg, timeout: 8000 })
  }
}

async function doCreateEntry(cls: SchoolClass) {
  if (!curriculumSubjectId.value || !selectedTeacher.value) return
  try {
    const { data } = await api.post<{ id: number }>(`/classes/${cls.id}/curriculum`, {
      class_id: cls.id,
      subject_id: curriculumSubjectId.value,
      hours_per_week: defaultHours.value,
      teacher_id: selectedTeacher.value.id,
    })
    const subj = subjectsStore.subjects.find((s) => s.id === curriculumSubjectId.value)
    allClusterEntries.value = [...allClusterEntries.value, {
      id: data.id,
      class_id: cls.id,
      class_name: cls.name,
      year_level: cls.year_level,
      school_id: cls.school_id,
      subject_id: curriculumSubjectId.value!,
      subject_name: subj?.name ?? '',
      hours_per_week: defaultHours.value,
      teacher_id: selectedTeacher.value.id,
      teacher_name: selectedTeacher.value.name,
    }]
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: unknown } } }
    const status = err?.response?.status ?? '?'
    const detail = err?.response?.data?.detail
    const msg = detail
      ? (typeof detail === 'string' ? detail : JSON.stringify(detail))
      : 'Sem detalhe'
    console.error('[doCreateEntry] HTTP', status, detail)
    $q.notify({
      type: 'negative',
      message: `Erro ${status} ao criar entrada curricular`,
      caption: msg,
      timeout: 8000,
    })
  }
}

async function assignAllClasses() {
  for (const cls of curriculumAllClasses.value) {
    if (!isClassAssigned(cls.id)) await toggleClass(cls, true)
  }
}

async function removeAllClasses() {
  for (const cls of curriculumAllClasses.value) {
    if (isClassAssigned(cls.id)) await toggleClass(cls, false)
  }
}

async function assignSchoolClasses(classes: SchoolClass[]) {
  for (const cls of classes) {
    if (!isClassAssigned(cls.id)) await toggleClass(cls, true)
  }
}

// Availability
const availabilityDialog = ref(false)
const availYear = ref<number | null>(null)
const availabilityMap = ref<Map<string, boolean>>(new Map())
const uniqueSlots = ref<number[]>([])

function isAvailable(day: number, slot: number) {
  return availabilityMap.value.get(`${day}_${slot}`) !== false
}

function toggleAvailability(day: number, slot: number) {
  const key = `${day}_${slot}`
  availabilityMap.value.set(key, !isAvailable(day, slot))
}

onMounted(async () => {
  await Promise.all([
    teachersStore.fetchAll(),
    clustersStore.fetchAll(),
    schoolsStore.fetchAll(),
    yearsStore.fetchAll(),
    subjectsStore.fetchAll(),
  ])
})

function openCreate() {
  editing.value = null
  form.value = {
    cluster_id: clustersStore.clusters[0]?.id ?? null,
    name: '',
    email: '',
    max_daily_lessons: 5,
    preferred_free_day: null,
    min_start_slot: null,
    max_end_slot: null,
    preferred_shift: null,
    max_consecutive_lessons: null,
    teaching_component: null,
  }
  dialog.value = true
}

function openEdit(row: Teacher) {
  editing.value = row
  form.value = {
    cluster_id: row.cluster_id,
    name: row.name,
    email: row.email || '',
    max_daily_lessons: row.max_daily_lessons,
    preferred_free_day: row.preferred_free_day ?? null,
    min_start_slot: row.min_start_slot ?? null,
    max_end_slot: row.max_end_slot ?? null,
    preferred_shift: row.preferred_shift ?? null,
    max_consecutive_lessons: row.max_consecutive_lessons ?? null,
    teaching_component: row.teaching_component ?? null,
  }
  dialog.value = true
}

async function save() {
  try {
    if (editing.value) {
      const payload = {
        name: form.value.name,
        email: form.value.email || null,
        max_daily_lessons: form.value.max_daily_lessons,
        preferred_free_day: form.value.preferred_free_day,
        min_start_slot: form.value.min_start_slot,
        max_end_slot: form.value.max_end_slot,
        preferred_shift: form.value.preferred_shift,
        max_consecutive_lessons: form.value.max_consecutive_lessons,
        teaching_component: form.value.teaching_component,
      }
      await teachersStore.update(editing.value.id, payload)
      $q.notify({ type: 'positive', message: 'Atualizado' })
    } else {
      if (!form.value.cluster_id) return
      await teachersStore.create({ ...form.value, cluster_id: form.value.cluster_id } as Parameters<typeof teachersStore.create>[0])
      $q.notify({ type: 'positive', message: 'Criado' })
    }
    dialog.value = false
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erro ao guardar'
    $q.notify({ type: 'negative', message: String(msg) })
  }
}

async function openSchools(teacher: Teacher) {
  selectedTeacher.value = teacher
  schoolAssignments.value = await teachersStore.fetchSchoolAssignments(teacher.id)
  schoolsDialog.value = true
}

async function addSchoolAssignment() {
  if (!selectedTeacher.value || !newAssignment.value.school_id || !newAssignment.value.academic_year_id) return
  const data = await teachersStore.addSchoolAssignment(selectedTeacher.value.id, {
    school_id: newAssignment.value.school_id,
    academic_year_id: newAssignment.value.academic_year_id,
    travel_time_minutes: newAssignment.value.travel_time_minutes,
  })
  schoolAssignments.value.push(data)
}

async function removeSchoolAssignment(id: number) {
  await teachersStore.removeSchoolAssignment(id)
  schoolAssignments.value = schoolAssignments.value.filter((a) => a.id !== id)
}

async function openSubjects(teacher: Teacher) {
  selectedTeacher.value = teacher
  teacherSubjects.value = await teachersStore.fetchSubjects(teacher.id)
  subjectsDialog.value = true
}

async function addSubject() {
  if (!selectedTeacher.value || !newSubjectId.value) return
  const data = await teachersStore.addSubject(selectedTeacher.value.id, newSubjectId.value)
  teacherSubjects.value.push(data)
  newSubjectId.value = null
}

async function removeSubject(subjectId: number) {
  if (!selectedTeacher.value) return
  await teachersStore.removeSubject(selectedTeacher.value.id, subjectId)
  teacherSubjects.value = teacherSubjects.value.filter((ts) => ts.subject_id !== subjectId)
}

async function openAvailability(teacher: Teacher) {
  selectedTeacher.value = teacher
  availYear.value = yearsStore.years.find((y) => y.is_active)?.id ?? null
  availabilityDialog.value = true
  if (availYear.value) await loadAvailability()
}

async function loadAvailability() {
  if (!selectedTeacher.value || !availYear.value) return
  const slots = await api.get('/time-slots', { params: { academic_year_id: availYear.value } })
  const slotNums = [...new Set((slots.data as { slot_number: number }[]).map((s) => s.slot_number))].sort((a, b) => a - b)
  uniqueSlots.value = slotNums

  const avail = await teachersStore.fetchAvailability(selectedTeacher.value.id, availYear.value)
  availabilityMap.value = new Map()
  // default all available
  for (let d = 0; d < 5; d++) {
    for (const s of slotNums) {
      availabilityMap.value.set(`${d}_${s}`, true)
    }
  }
  for (const a of avail) {
    availabilityMap.value.set(`${a.day_of_week}_${a.slot_number}`, a.is_available)
  }
}

async function saveAvailability() {
  if (!selectedTeacher.value || !availYear.value) return
  const availabilities = []
  for (let d = 0; d < 5; d++) {
    for (const s of uniqueSlots.value) {
      availabilities.push({
        teacher_id: selectedTeacher.value.id,
        academic_year_id: availYear.value,
        day_of_week: d,
        slot_number: s,
        is_available: isAvailable(d, s),
      })
    }
  }
  await teachersStore.setAvailabilityBulk(selectedTeacher.value.id, availYear.value, availabilities)
  $q.notify({ type: 'positive', message: 'Disponibilidade guardada' })
}

function confirmDelete(row: Teacher) {
  $q.dialog({
    title: 'Confirmar eliminação',
    message: `Eliminar "${row.name}"?`,
    ok: { label: 'Eliminar', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    await teachersStore.remove(row.id)
    $q.notify({ type: 'positive', message: 'Eliminado' })
  })
}
</script>
