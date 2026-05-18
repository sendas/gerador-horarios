<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Turmas</div>
      <q-btn color="primary" icon="add" label="Nova" @click="openCreate" />
      <q-btn color="secondary" icon="upload" label="Importar" @click="showImport = true" class="q-ml-sm" />
    </div>

    <ImportDialog
      v-model="showImport"
      title="Importar Turmas"
      endpoint="/imports/classes"
      :extra-params="{ school_id: selectedSchoolId, academic_year_id: selectedYearId }"
      entity-type="classes"
      @done="classesStore.fetchAll()"
    />

    <q-table :rows="classesStore.classes" :columns="columns" row-key="id" :loading="classesStore.loading">
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn flat round dense icon="menu_book" color="primary" title="Currículo" @click="openCurriculum(props.row)" />
          <q-btn flat round dense icon="edit" @click="openEdit(props.row)" />
          <q-btn flat round dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Class dialog -->
    <q-dialog v-model="dialog">
      <q-card style="min-width: 450px">
        <q-card-section><div class="text-h6">{{ editing ? 'Editar' : 'Nova' }} Turma</div></q-card-section>
        <q-card-section>
          <q-form @submit="save">
            <q-select v-model="form.school_id" :options="schoolOptions" label="Escola *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-select v-model="form.academic_year_id" :options="yearOptions" label="Ano Letivo *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.name" label="Nome da turma *" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model.number="form.year_level" label="Ano de escolaridade *" type="number" min="1" />
            <q-input v-model.number="form.num_students" label="Nº de alunos" type="number" min="1" />
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" :label="editing ? 'Guardar' : 'Criar'" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Curriculum dialog -->
    <q-dialog v-model="curriculumDialog" full-width>
      <q-card>
        <q-card-section class="row items-center">
          <div class="text-h6">Currículo: {{ selectedClass?.name }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-table :rows="curriculumEntries" :columns="currColumns" row-key="id" dense flat>
            <template #top>
              <q-btn color="primary" icon="add" label="Adicionar disciplina" @click="openAddEntry" />
            </template>
            <template #body-cell-subject="props">
              <q-td :props="props">{{ subjectName(props.row.subject_id) }}</q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props">
                <q-btn flat round dense icon="delete" color="negative" @click="removeEntry(props.row.id)" />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Add curriculum entry dialog -->
    <q-dialog v-model="addEntryDialog">
      <q-card style="min-width: 350px">
        <q-card-section><div class="text-h6">Adicionar Disciplina</div></q-card-section>
        <q-card-section>
          <q-form @submit="addEntry">
            <q-select v-model="entryForm.subject_id" :options="subjectOptions" label="Disciplina *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model.number="entryForm.hours_per_week" label="Horas/semana *" type="number" step="0.5" min="0.5" :rules="[v => v > 0 || 'Obrigatório']" />
            <q-checkbox v-model="entryForm.is_split" label="Aula dividida?" />
            <q-input v-if="entryForm.is_split" v-model.number="entryForm.split_count" label="Nº de partes" type="number" min="2" />
            <q-input
              v-if="entryForm.is_split && entryForm.split_count > 1"
              v-model.number="entryForm.consecutive_pairs"
              label="Pares consecutivos (blocos de 2)"
              type="number"
              min="0"
              :max="Math.floor(entryForm.split_count / 2)"
              hint="Quantas das partes devem ser dadas em bloco (2 tempos consecutivos)."
            />
            <q-separator class="q-my-sm" />
            <q-checkbox v-model="entryForm.is_semestral" label="Disciplina semestral?" />
            <template v-if="entryForm.is_semestral">
              <q-select
                v-model="entryForm.semester"
                :options="semesterOptions"
                label="Semestre *"
                emit-value
                map-options
                class="q-mt-sm"
              />
              <q-select
                v-model="entryForm.paired_entry_id"
                :options="semestralEntryOptions"
                label="Disciplina par (outro semestre)"
                emit-value
                map-options
                clearable
                class="q-mt-sm"
                hint="Selecione a disciplina que ocorre no outro semestre no mesmo horário."
              />
            </template>
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" label="Adicionar" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useClassesStore, type SchoolClass, type CurriculumEntry } from 'stores/classes'
import { useSchoolsStore } from 'stores/schools'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useSubjectsStore } from 'stores/subjects'
import ImportDialog from 'components/ImportDialog.vue'

const $q = useQuasar()
const classesStore = useClassesStore()
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()
const subjectsStore = useSubjectsStore()

const showImport = ref(false)
const selectedSchoolId = computed(() => schoolsStore.schools[0]?.id ?? null)
const selectedYearId = computed(() => yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null)

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'year_level', label: 'Ano', field: 'year_level', align: 'center' as const },
  { name: 'num_students', label: 'Alunos', field: 'num_students', align: 'center' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const currColumns = [
  { name: 'subject', label: 'Disciplina', field: 'subject_id', align: 'left' as const },
  { name: 'hours_per_week', label: 'Horas/sem', field: 'hours_per_week', align: 'center' as const },
  { name: 'split_count', label: 'Partes', field: 'split_count', align: 'center' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const dialog = ref(false)
const editing = ref<null | SchoolClass>(null)
const form = ref({ school_id: null as number | null, academic_year_id: null as number | null, name: '', year_level: 5, num_students: 25 })

const curriculumDialog = ref(false)
const addEntryDialog = ref(false)
const selectedClass = ref<SchoolClass | null>(null)
const curriculumEntries = ref<CurriculumEntry[]>([])
const entryForm = ref({
  subject_id: null as number | null,
  hours_per_week: 2,
  is_split: false,
  split_count: 2,
  consecutive_pairs: 0,
  is_semestral: false,
  semester: null as number | null,
  paired_entry_id: null as number | null,
})

const schoolOptions = computed(() => schoolsStore.schools.map((s) => ({ label: s.name, value: s.id })))
const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const subjectOptions = computed(() => subjectsStore.subjects.map((s) => ({ label: s.name, value: s.id })))

const semesterOptions = [
  { label: '1.º Semestre', value: 1 },
  { label: '2.º Semestre', value: 2 },
]

// Semestral entries of the selected class that can be paired
const semestralEntryOptions = computed(() =>
  curriculumEntries.value
    .filter((e) => e.is_semestral && e.id !== undefined)
    .map((e) => ({ label: subjectName(e.subject_id), value: e.id }))
)

function subjectName(id: number) {
  return subjectsStore.subjects.find((s) => s.id === id)?.name ?? '—'
}

onMounted(async () => {
  await Promise.all([
    classesStore.fetchAll(),
    schoolsStore.fetchAll(),
    yearsStore.fetchAll(),
    subjectsStore.fetchAll(),
  ])
})

function openCreate() {
  editing.value = null
  form.value = { school_id: null, academic_year_id: null, name: '', year_level: 5, num_students: 25 }
  dialog.value = true
}

function openEdit(row: SchoolClass) {
  editing.value = row
  form.value = { school_id: row.school_id, academic_year_id: row.academic_year_id, name: row.name, year_level: row.year_level, num_students: row.num_students }
  dialog.value = true
}

async function save() {
  if (!form.value.school_id || !form.value.academic_year_id) return
  try {
    if (editing.value) {
      await classesStore.update(editing.value.id, form.value)
      $q.notify({ type: 'positive', message: 'Atualizada' })
    } else {
      await classesStore.create(form.value as Parameters<typeof classesStore.create>[0])
      $q.notify({ type: 'positive', message: 'Criada' })
    }
    dialog.value = false
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar' })
  }
}

async function openCurriculum(row: SchoolClass) {
  selectedClass.value = row
  curriculumEntries.value = await classesStore.fetchCurriculum(row.id)
  curriculumDialog.value = true
}

function openAddEntry() {
  entryForm.value = {
    subject_id: null,
    hours_per_week: 2,
    is_split: false,
    split_count: 2,
    consecutive_pairs: 0,
    is_semestral: false,
    semester: null,
    paired_entry_id: null,
  }
  addEntryDialog.value = true
}

async function addEntry() {
  if (!selectedClass.value || !entryForm.value.subject_id) return
  try {
    const payload = {
      subject_id: entryForm.value.subject_id,
      hours_per_week: entryForm.value.hours_per_week,
      is_split: entryForm.value.is_split,
      split_count: entryForm.value.split_count,
      consecutive_pairs: entryForm.value.consecutive_pairs,
      is_semestral: entryForm.value.is_semestral,
      semester: entryForm.value.is_semestral ? entryForm.value.semester : null,
      paired_entry_id: entryForm.value.is_semestral ? entryForm.value.paired_entry_id : null,
      class_id: selectedClass.value.id,
    }
    const entry = await classesStore.addCurriculumEntry(selectedClass.value.id, payload)
    curriculumEntries.value.push(entry)
    addEntryDialog.value = false
    $q.notify({ type: 'positive', message: 'Disciplina adicionada' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao adicionar' })
  }
}

async function removeEntry(entryId: number) {
  await classesStore.removeCurriculumEntry(entryId)
  curriculumEntries.value = curriculumEntries.value.filter((e) => e.id !== entryId)
  $q.notify({ type: 'positive', message: 'Removida' })
}

function confirmDelete(row: SchoolClass) {
  $q.dialog({
    title: 'Confirmar eliminação',
    message: `Eliminar "${row.name}"?`,
    ok: { label: 'Eliminar', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    await classesStore.remove(row.id)
    $q.notify({ type: 'positive', message: 'Eliminada' })
  })
}
</script>
