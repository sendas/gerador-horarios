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

    <q-table :rows="teachersStore.teachers" :columns="columns" row-key="id" :loading="teachersStore.loading">
      <template #body-cell-preferred_free_day="props">
        <q-td :props="props">{{ props.row.preferred_free_day !== null && props.row.preferred_free_day !== undefined ? DAYS[props.row.preferred_free_day] : '—' }}</q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn unelevated size="sm" color="info" icon="school" label="Escolas" @click="openSchools(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="secondary" icon="book" label="Disciplinas" @click="openSubjects(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="positive" icon="event_available" label="Disponibilidade" @click="openAvailability(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openEdit(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Teacher dialog -->
    <q-dialog v-model="dialog">
      <q-card style="min-width: 450px">
        <q-card-section><div class="text-h6">{{ editing ? 'Editar' : 'Novo' }} Professor</div></q-card-section>
        <q-card-section>
          <q-form @submit="save">
            <q-select v-model="form.cluster_id" :options="clusterOptions" label="Agrupamento *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.name" label="Nome *" :rules="[v => !!v || 'Obrigatório']" />
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
                <q-btn flat round dense icon="delete" color="negative" @click="removeSchoolAssignment(a.id)" />
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
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useTeachersStore, type Teacher } from 'stores/teachers'
import { useClustersStore } from 'stores/clusters'
import { useSchoolsStore } from 'stores/schools'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useSubjectsStore } from 'stores/subjects'
import { api } from 'boot/axios'
import ImportDialog from 'components/ImportDialog.vue'

const $q = useQuasar()
const teachersStore = useTeachersStore()
const clustersStore = useClustersStore()

const showImport = ref(false)
const selectedClusterId = computed(() => clustersStore.clusters[0]?.id ?? null)
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()
const subjectsStore = useSubjectsStore()

const DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'email', label: 'Email', field: 'email', align: 'left' as const },
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
    cluster_id: null,
    name: '',
    email: '',
    max_daily_lessons: 5,
    preferred_free_day: null,
    min_start_slot: null,
    max_end_slot: null,
    preferred_shift: null,
    max_consecutive_lessons: null,
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
  }
  dialog.value = true
}

async function save() {
  if (!form.value.cluster_id) return
  try {
    const payload = { ...form.value, cluster_id: form.value.cluster_id }
    if (editing.value) {
      await teachersStore.update(editing.value.id, payload)
      $q.notify({ type: 'positive', message: 'Atualizado' })
    } else {
      await teachersStore.create(payload as Parameters<typeof teachersStore.create>[0])
      $q.notify({ type: 'positive', message: 'Criado' })
    }
    dialog.value = false
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar' })
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
