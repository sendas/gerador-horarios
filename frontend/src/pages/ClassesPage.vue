<template>
  <q-page padding>
    <div class="row items-center q-mb-sm">
      <div class="text-h5 col">Turmas</div>
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn color="primary" icon="add" label="Nova" @click="openCreate" class="q-ml-sm" />
      <q-btn color="secondary" icon="upload" label="Importar Turmas" @click="showImport = true" class="q-ml-sm" />
    </div>

    <!-- Filters: school and year level -->
    <div class="row items-center q-mb-md q-gutter-xs">
      <div class="text-caption text-grey-6 q-mr-xs">Escola:</div>
      <q-chip
        v-for="school in schoolsStore.schools" :key="school.id"
        clickable
        :color="filterSchoolId === school.id ? 'primary' : 'grey-3'"
        :text-color="filterSchoolId === school.id ? 'white' : 'dark'"
        dense
        @click="filterSchoolId = filterSchoolId === school.id ? null : school.id"
      >{{ school.name }}</q-chip>
      <q-separator vertical class="q-mx-sm" />
      <div class="text-caption text-grey-6 q-mr-xs">Ano:</div>
      <q-chip
        v-for="yl in availableYearLevels" :key="yl"
        clickable
        :color="filterYearLevel === yl ? 'secondary' : 'grey-3'"
        :text-color="filterYearLevel === yl ? 'white' : 'dark'"
        dense
        @click="filterYearLevel = filterYearLevel === yl ? null : yl"
      >{{ yl }}.º</q-chip>
    </div>

    <ImportDialog
      v-model="showImport"
      title="Importar Turmas"
      endpoint="/imports/classes"
      :extra-params="{ school_id: selectedSchoolId, academic_year_id: selectedYearId }"
      entity-type="classes"
      @done="classesStore.fetchAll()"
    />

    <q-table :rows="filteredClasses" :columns="columns" row-key="id" :loading="classesStore.loading" :filter="search" sort-by="name">
      <template #body-cell-notes="props">
        <q-td :props="props">
          <span v-if="props.row.notes" class="text-caption text-grey-8">
            <q-icon name="info" size="xs" color="info" class="q-mr-xs" />{{ props.row.notes }}
          </span>
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn unelevated size="sm" color="secondary" icon="call_split" label="Turnos" @click="openGroups(props.row)" class="q-mr-xs">
            <q-tooltip>Gerir grupos/turnos de disciplinas simultâneas desta turma</q-tooltip>
          </q-btn>
          <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openEdit(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="confirmDelete(props.row)" />
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

    <!-- Groups/Turnos dialog -->
    <q-dialog v-model="groupsDialog" full-width>
      <q-card style="max-width:860px;width:100%">
        <q-card-section class="row items-center bg-secondary text-white">
          <div>
            <div class="text-h6"><q-icon name="call_split" class="q-mr-sm" />Turnos e Grupos — {{ selectedClass?.name }}</div>
            <div class="text-caption opacity-80">Disciplinas que ocorrem em simultâneo para subgrupos da turma</div>
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <!-- Curriculum read-only — redirects to plans for editing -->
          <q-banner dense rounded class="bg-blue-1 text-blue-10 q-mb-md">
            <template #avatar><q-icon name="menu_book" color="blue-7" /></template>
            Para adicionar, editar ou remover disciplinas desta turma, usa
            <router-link to="/curriculum-plans" class="text-blue-9 text-weight-medium" @click="groupsDialog = false">
              Planos Curriculares
            </router-link>.
            A lista abaixo é apenas de consulta.
          </q-banner>

          <div class="text-subtitle2 q-mb-xs text-grey-8">Disciplinas desta turma</div>
          <div v-if="curriculumEntries.length === 0" class="text-caption text-grey-5 q-mb-md q-py-sm">
            Nenhuma disciplina atribuída — aplica um plano curricular primeiro.
          </div>
          <div v-else class="row q-gutter-xs q-mb-md flex-wrap">
            <q-chip
              v-for="e in curriculumEntries" :key="e.id"
              dense square size="sm"
              color="grey-2" text-color="dark"
            >
              {{ subjectName(e.subject_id) }}
              <span class="text-grey-6 q-ml-xs">{{ e.hours_per_week }}h</span>
              <q-badge v-if="e.is_semestral" :color="e.semester === 1 ? 'blue-7' : 'orange-7'"
                class="q-ml-xs" :label="e.semester === 1 ? '1.ºS' : '2.ºS'" />
            </q-chip>
          </div>

          <q-separator class="q-mb-md" />

          <!-- Subject groups / turnos -->
          <div class="row items-center q-mb-sm">
            <div class="text-subtitle2 col">Turnos (grupos de disciplinas simultâneas)</div>
            <q-btn color="secondary" icon="add" size="sm" label="Novo turno" unelevated @click="openAddGroup" />
          </div>
          <div v-if="subjectGroups.length === 0" class="text-caption text-grey-6 q-py-sm">
            Nenhum turno definido. Use turnos quando metade da turma tem uma disciplina e a outra metade tem outra ao mesmo tempo (ex: CN e FQ em laboratório).
          </div>
          <div v-for="group in subjectGroups" :key="group.id" class="q-mb-xs row items-center">
            <q-icon name="call_split" class="q-mr-xs text-secondary" />
            <span class="text-body2 q-mr-sm">{{ group.name }}</span>
            <q-chip
              v-for="ge in group.entries" :key="ge.id"
              dense removable
              @remove="removeGroupEntry(group.id, ge.id)"
              color="secondary" text-color="white" size="sm"
            >
              {{ entrySubjectName(ge.curriculum_entry_id) }}
            </q-chip>
            <q-btn unelevated size="sm" color="secondary" icon="add_circle" label="Adicionar" @click="openAddEntryToGroup(group)" class="q-ml-xs" />
            <q-space />
            <q-btn flat size="sm" color="negative" icon="delete" label="Apagar turno" @click="deleteGroup(group.id)" />
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

const $q = useQuasar()
const classesStore = useClassesStore()
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()
const subjectsStore = useSubjectsStore()

const search = ref('')
const showImport = ref(false)
const filterSchoolId = ref<number | null>(null)
const filterYearLevel = ref<number | null>(null)
const selectedSchoolId = computed(() => schoolsStore.schools[0]?.id ?? null)
const selectedYearId = computed(() => yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null)

const availableYearLevels = computed(() => {
  const yls = new Set(classesStore.classes.map((c) => c.year_level))
  return Array.from(yls).sort((a, b) => a - b)
})

const filteredClasses = computed(() => {
  return classesStore.classes.filter((c) => {
    if (filterSchoolId.value !== null && c.school_id !== filterSchoolId.value) return false
    if (filterYearLevel.value !== null && c.year_level !== filterYearLevel.value) return false
    return true
  })
})

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'year_level', label: 'Ano', field: 'year_level', align: 'center' as const },
  { name: 'num_students', label: 'Alunos', field: 'num_students', align: 'center' as const },
  { name: 'notes', label: 'Observações', field: 'notes', align: 'left' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const dialog = ref(false)
const editing = ref<null | SchoolClass>(null)
const form = ref({ school_id: null as number | null, academic_year_id: null as number | null, name: '', year_level: 5, num_students: 25, notes: '' })

const groupsDialog = ref(false)
const selectedClass = ref<SchoolClass | null>(null)
const curriculumEntries = ref<CurriculumEntry[]>([])

const schoolOptions = computed(() => schoolsStore.schools.map((s) => ({ label: s.name, value: s.id })))
const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))

function subjectName(id: number) {
  return subjectsStore.subjects.find((s) => s.id === id)?.name ?? '—'
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

async function openGroups(row: SchoolClass) {
  selectedClass.value = row
  curriculumEntries.value = await classesStore.fetchCurriculum(row.id)
  await loadSubjectGroups()
  groupsDialog.value = true
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
