<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Turmas</div>
      <q-btn color="primary" icon="add" label="Nova" @click="openCreate" />
      <q-btn color="secondary" icon="upload" label="Importar Turmas" @click="showImport = true" class="q-ml-sm" />
      <q-btn color="purple" icon="table_chart" label="Importar Currículo" @click="showCurriculumImport = true" class="q-ml-sm" />
    </div>

    <ImportDialog
      v-model="showImport"
      title="Importar Turmas"
      endpoint="/imports/classes"
      :extra-params="{ school_id: selectedSchoolId, academic_year_id: selectedYearId }"
      entity-type="classes"
      @done="classesStore.fetchAll()"
    />

    <ImportCurriculumDialog
      v-model="showCurriculumImport"
      @done="classesStore.fetchAll()"
    />

    <q-table :rows="classesStore.classes" :columns="columns" row-key="id" :loading="classesStore.loading">
      <template #body-cell-notes="props">
        <q-td :props="props">
          <span v-if="props.row.notes" class="text-caption text-grey-8">
            <q-icon name="info" size="xs" color="info" class="q-mr-xs" />{{ props.row.notes }}
          </span>
        </q-td>
      </template>
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
            <q-input v-model="form.notes" label="Observações" clearable hint="Ex: info de articulado, condições especiais" />
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
            <template #body-cell-semestral="props">
              <q-td :props="props">
                <q-badge v-if="props.row.is_semestral" :color="props.row.semester === 1 ? 'blue-7' : 'orange-7'" :label="props.row.semester === 1 ? '1.º Sem' : '2.º Sem'" />
              </q-td>
            </template>
            <template #body-cell-paired="props">
              <q-td :props="props">
                <span v-if="props.row.paired_entry_id" class="text-caption text-positive">
                  ⇄ {{ pairedSubjectName(props.row.paired_entry_id) }}
                </span>
              </q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props">
                <q-btn flat round dense icon="delete" color="negative" @click="removeEntry(props.row.id)" />
              </q-td>
            </template>
          </q-table>

          <q-separator class="q-my-md" />
          <div class="row items-center q-mb-sm">
            <div class="text-subtitle2 col">Turnos (Grupos de Disciplinas Simultâneas)</div>
            <q-btn color="secondary" icon="call_split" size="sm" label="Novo Turno" @click="openAddGroup" />
          </div>
          <div v-if="subjectGroups.length === 0" class="text-caption text-grey-6 q-mb-sm">
            Nenhum turno definido. Use turnos quando metade da turma tem uma disciplina e a outra metade tem outra ao mesmo tempo (ex: CN e FQ em laboratório).
          </div>
          <div v-for="group in subjectGroups" :key="group.id" class="q-mb-xs">
            <div class="row items-center">
              <q-icon name="call_split" class="q-mr-xs text-secondary" />
              <span class="text-body2 q-mr-sm">{{ group.name }}</span>
              <q-chip v-for="ge in group.entries" :key="ge.id" dense removable @remove="removeGroupEntry(group.id, ge.id)"
                color="secondary" text-color="white" size="sm">
                {{ entrySubjectName(ge.curriculum_entry_id) }}
              </q-chip>
              <q-btn flat round dense icon="add_circle" size="sm" color="secondary" @click="openAddEntryToGroup(group)" />
              <q-space />
              <q-btn flat round dense icon="delete" size="sm" color="negative" @click="deleteGroup(group.id)" />
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Add group entry dialog -->
    <q-dialog v-model="addGroupEntryDialog">
      <q-card style="min-width: 300px">
        <q-card-section><div class="text-h6">Adicionar ao Turno</div></q-card-section>
        <q-card-section>
          <q-select v-model="groupEntryForm.curriculum_entry_id" :options="availableForGroupOptions" label="Disciplina" emit-value map-options />
          <div class="row justify-end q-mt-md q-gutter-sm">
            <q-btn flat label="Cancelar" v-close-popup />
            <q-btn color="secondary" label="Adicionar" @click="addEntryToGroup" />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Add curriculum entry dialog -->
    <q-dialog v-model="addEntryDialog">
      <q-card style="min-width: 350px">
        <q-card-section><div class="text-h6">Adicionar Disciplina</div></q-card-section>
        <q-card-section>
          <q-form @submit="addEntry">
            <q-select
              v-model="entryForm.subject_id"
              :options="subjectOptions"
              label="Disciplina *"
              emit-value map-options
              :rules="[v => !!v || 'Obrigatório']"
              @update:model-value="onSubjectChange"
            />
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
            <div class="text-caption text-weight-medium q-mb-xs">
              <q-icon name="event" class="q-mr-xs" />Regime Semestral
            </div>
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
              <q-banner
                v-if="entryForm.semester"
                dense
                rounded
                class="bg-blue-1 text-blue-10 q-mt-sm q-mb-xs"
              >
                <template #avatar><q-icon name="info" color="blue-7" /></template>
                Disciplina semestral: ocorre apenas no {{ entryForm.semester === 1 ? '1.º' : '2.º' }} semestre. Para emparelhamento, selecione a disciplina que ocorre no outro semestre no mesmo horário.
              </q-banner>
              <q-select
                v-model="entryForm.paired_entry_id"
                :options="semestralEntryOptions"
                label="Emparelhar com (outro semestre no mesmo horário)"
                emit-value
                map-options
                clearable
                class="q-mt-sm"
                hint="Selecione a disciplina que ocorre no outro semestre no mesmo horário."
              />
            </template>
            <q-separator class="q-my-sm" />
            <div class="text-caption text-weight-medium q-mb-xs">
              <q-icon name="call_split" class="q-mr-xs" />Turno / Desdobramento
            </div>
            <q-banner dense rounded class="bg-blue-1 text-blue-10 q-mb-sm" v-if="entryForm.is_split">
              <template #avatar><q-icon name="info" color="blue-7" /></template>
              Para turnos (ex: metade da turma em CN, outra em FQ ao mesmo tempo), configure o emparelhamento semestral acima ou use os Grupos de Disciplinas.
            </q-banner>
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
import { api } from 'boot/axios'
import ImportDialog from 'components/ImportDialog.vue'
import ImportCurriculumDialog from 'components/ImportCurriculumDialog.vue'

const $q = useQuasar()
const classesStore = useClassesStore()
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()
const subjectsStore = useSubjectsStore()

const showImport = ref(false)
const showCurriculumImport = ref(false)
const selectedSchoolId = computed(() => schoolsStore.schools[0]?.id ?? null)
const selectedYearId = computed(() => yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null)

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'year_level', label: 'Ano', field: 'year_level', align: 'center' as const },
  { name: 'num_students', label: 'Alunos', field: 'num_students', align: 'center' as const },
  { name: 'notes', label: 'Observações', field: 'notes', align: 'left' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const currColumns = [
  { name: 'subject', label: 'Disciplina', field: 'subject_id', align: 'left' as const },
  { name: 'hours_per_week', label: 'Horas/sem', field: 'hours_per_week', align: 'center' as const },
  { name: 'split_count', label: 'Partes', field: 'split_count', align: 'center' as const },
  { name: 'semestral', label: 'Semestre', field: 'semester', align: 'center' as const },
  { name: 'paired', label: 'Par c/ semestre oposto', field: 'paired_entry_id', align: 'left' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const dialog = ref(false)
const editing = ref<null | SchoolClass>(null)
const form = ref({ school_id: null as number | null, academic_year_id: null as number | null, name: '', year_level: 5, num_students: 25, notes: '' })

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
  _editingId: undefined as number | undefined,
})

const schoolOptions = computed(() => schoolsStore.schools.map((s) => ({ label: s.name, value: s.id })))
const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const subjectOptions = computed(() => subjectsStore.subjects.map((s) => ({ label: s.name, value: s.id })))

const STRUCT_DEFAULTS: Record<string, { split_count: number; consecutive_pairs: number }> = {
  '1':     { split_count: 1, consecutive_pairs: 0 },
  '1+1':   { split_count: 2, consecutive_pairs: 0 },
  '2':     { split_count: 2, consecutive_pairs: 1 },
  '2+1':   { split_count: 3, consecutive_pairs: 1 },
  '1+1+1': { split_count: 3, consecutive_pairs: 0 },
}

function onSubjectChange(subjectId: number | null) {
  const subj = subjectsStore.subjects.find((s) => s.id === subjectId)
  if (!subj) return
  const d = STRUCT_DEFAULTS[subj.weekly_structure] ?? { split_count: 2, consecutive_pairs: 0 }
  entryForm.value.split_count = d.split_count
  entryForm.value.consecutive_pairs = d.consecutive_pairs
  entryForm.value.is_split = d.split_count > 1
  entryForm.value.is_semestral = subj.regime === 'semestral'
  entryForm.value.semester = subj.default_semester ?? null
}

const semesterOptions = [
  { label: '1.º Semestre', value: 1 },
  { label: '2.º Semestre', value: 2 },
]

// Semestral entries of the selected class that can be paired
const semestralEntryOptions = computed(() =>
  curriculumEntries.value
    .filter((e) => e.is_semestral && e.id !== undefined && e.id !== entryForm.value._editingId)
    .map((e) => ({ label: subjectName(e.subject_id), value: e.id }))
)

function subjectName(id: number) {
  return subjectsStore.subjects.find((s) => s.id === id)?.name ?? '—'
}

function pairedSubjectName(entryId: number) {
  const e = curriculumEntries.value.find(e => e.id === entryId)
  return e ? subjectName(e.subject_id) : '?'
}

// Subject groups (turnos)
interface SubjectGroupEntry { id: number; group_id: number; curriculum_entry_id: number }
interface SubjectGroupItem { id: number; name: string; academic_year_id: number; entries: SubjectGroupEntry[] }
const subjectGroups = ref<SubjectGroupItem[]>([])
const addGroupEntryDialog = ref(false)
const selectedGroupForEntry = ref<SubjectGroupItem | null>(null)
const groupEntryForm = ref({ curriculum_entry_id: null as number | null })

const availableForGroupOptions = computed(() => {
  const inGroup = new Set(
    subjectGroups.value.flatMap(g => g.entries.map(e => e.curriculum_entry_id))
  )
  return curriculumEntries.value
    .filter(e => !inGroup.has(e.id))
    .map(e => ({ label: subjectName(e.subject_id), value: e.id }))
})

function entrySubjectName(curriculum_entry_id: number) {
  const e = curriculumEntries.value.find(e => e.id === curriculum_entry_id)
  return e ? subjectName(e.subject_id) : '?'
}

async function loadSubjectGroups() {
  if (!selectedClass.value) return
  const yearId = selectedClass.value.academic_year_id
  const { data } = await api.get<SubjectGroupItem[]>('/subject-groups', { params: { academic_year_id: yearId } })
  const classEntryIds = new Set(curriculumEntries.value.map(e => e.id))
  subjectGroups.value = data.filter(g => g.entries.some(e => classEntryIds.has(e.curriculum_entry_id)))
}

async function openAddGroup() {
  if (!selectedClass.value) return
  const yearId = selectedClass.value.academic_year_id
  const name = `Turno ${selectedClass.value.name}`
  const { data } = await api.post<SubjectGroupItem>('/subject-groups', { name, academic_year_id: yearId })
  subjectGroups.value.push(data)
}

function openAddEntryToGroup(group: SubjectGroupItem) {
  selectedGroupForEntry.value = group
  groupEntryForm.value = { curriculum_entry_id: null }
  addGroupEntryDialog.value = true
}

async function addEntryToGroup() {
  if (!selectedGroupForEntry.value || !groupEntryForm.value.curriculum_entry_id) return
  const { data } = await api.post<SubjectGroupEntry>(
    `/subject-groups/${selectedGroupForEntry.value.id}/entries`,
    { curriculum_entry_id: groupEntryForm.value.curriculum_entry_id }
  )
  const group = subjectGroups.value.find(g => g.id === selectedGroupForEntry.value!.id)
  if (group) group.entries.push(data)
  addGroupEntryDialog.value = false
}

async function removeGroupEntry(groupId: number, entryId: number) {
  await api.delete(`/subject-groups/${groupId}/entries/${entryId}`)
  const group = subjectGroups.value.find(g => g.id === groupId)
  if (group) group.entries = group.entries.filter(e => e.id !== entryId)
}

async function deleteGroup(groupId: number) {
  await api.delete(`/subject-groups/${groupId}`)
  subjectGroups.value = subjectGroups.value.filter(g => g.id !== groupId)
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
  form.value = { school_id: null, academic_year_id: null, name: '', year_level: 5, num_students: 25, notes: '' }
  dialog.value = true
}

function openEdit(row: SchoolClass) {
  editing.value = row
  form.value = { school_id: row.school_id, academic_year_id: row.academic_year_id, name: row.name, year_level: row.year_level, num_students: row.num_students, notes: row.notes ?? '' }
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
  await loadSubjectGroups()
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
    _editingId: undefined,
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
    // Bidirectional pairing: also set paired_entry_id on the other entry
    if (payload.paired_entry_id) {
      const updated = await classesStore.updateCurriculumEntry(payload.paired_entry_id, { paired_entry_id: entry.id })
      const idx = curriculumEntries.value.findIndex(e => e.id === payload.paired_entry_id)
      if (idx !== -1) curriculumEntries.value[idx] = updated
    }
    addEntryDialog.value = false
    $q.notify({ type: 'positive', message: 'Disciplina adicionada' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao adicionar' })
  }
}

async function removeEntry(entryId: number) {
  const entry = curriculumEntries.value.find(e => e.id === entryId)
  // Clear bidirectional pairing before removing
  if (entry?.paired_entry_id) {
    const updated = await classesStore.updateCurriculumEntry(entry.paired_entry_id, { paired_entry_id: null })
    const idx = curriculumEntries.value.findIndex(e => e.id === entry.paired_entry_id)
    if (idx !== -1) curriculumEntries.value[idx] = updated
  }
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
