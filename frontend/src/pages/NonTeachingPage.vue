<template>
  <q-page padding>
    <div class="text-h5 q-mb-md">Serviço Não Letivo</div>

    <div class="row q-col-gutter-md">
      <!-- Types section -->
      <div class="col-12 col-md-5">
        <q-card>
          <q-card-section>
            <div class="row items-center">
              <div class="text-h6 col">Tipos</div>
              <q-btn unelevated size="sm" color="primary" icon="add" label="Novo" @click="openTypeCreate" />
            </div>
          </q-card-section>
          <q-list separator>
            <q-item v-for="t in types" :key="t.id">
              <q-item-section avatar>
                <div :style="{ background: t.color, width: '20px', height: '20px', borderRadius: '50%' }" />
              </q-item-section>
              <q-item-section>{{ t.name }}</q-item-section>
              <q-item-section side>
                <div class="row">
                  <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openTypeEdit(t)" class="q-mr-xs" />
                  <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="deleteType(t.id)" />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>

      <!-- Assignments section -->
      <div class="col-12 col-md-7">
        <q-card>
          <q-card-section>
            <div class="text-h6 q-mb-sm">Atribuições</div>
            <div class="row q-col-gutter-sm q-mb-md">
              <div class="col-6">
                <q-select v-model="filterTeacher" :options="teacherOptions" label="Professor" emit-value map-options dense clearable @update:model-value="loadAssignments" />
              </div>
              <div class="col-6">
                <q-select v-model="filterYear" :options="yearOptions" label="Ano Letivo" emit-value map-options dense @update:model-value="loadAssignments" />
              </div>
            </div>

            <div class="row items-center q-mb-sm">
              <q-space />
              <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
                <template #prepend><q-icon name="search" /></template>
              </q-input>
            </div>
            <q-table :rows="assignments" :columns="assignCols" row-key="id" dense flat :filter="search" sort-by="teacher_name">
              <template #top>
                <q-btn color="primary" icon="add" label="Adicionar" @click="openAssignCreate" dense />
              </template>
              <template #body-cell-type="props">
                <q-td :props="props">{{ typeName(props.row.non_teaching_type_id) }}</q-td>
              </template>
              <template #body-cell-day="props">
                <q-td :props="props">{{ DAYS[props.row.day_of_week] }}</q-td>
              </template>
              <template #body-cell-actions="props">
                <q-td :props="props">
                  <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="deleteAssignment(props.row.id)" />
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Type dialog -->
    <q-dialog v-model="typeDialog">
      <q-card style="min-width:320px">
        <q-card-section><div class="text-h6">{{ editingType ? 'Editar' : 'Novo' }} Tipo</div></q-card-section>
        <q-card-section>
          <q-form @submit="saveType">
            <q-select v-model="typeForm.cluster_id" :options="clusterOptions" label="Agrupamento *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="typeForm.name" label="Nome *" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="typeForm.color" label="Cor" />
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" :label="editingType ? 'Guardar' : 'Criar'" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Assignment dialog -->
    <q-dialog v-model="assignDialog">
      <q-card style="min-width:400px">
        <q-card-section><div class="text-h6">Nova Atribuição</div></q-card-section>
        <q-card-section>
          <q-form @submit="createAssignment">
            <q-select v-model="assignForm.teacher_id" :options="teacherOptions" label="Professor *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-select v-model="assignForm.non_teaching_type_id" :options="typeOptions" label="Tipo *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-select v-model="assignForm.academic_year_id" :options="yearOptions" label="Ano Letivo *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-select v-model="assignForm.day_of_week" :options="dayOptions" label="Dia *" emit-value map-options :rules="[v => v !== null || 'Obrigatório']" />
            <q-input v-model.number="assignForm.slot_number" label="Nº Tempo *" type="number" min="1" :rules="[v => v > 0 || 'Obrigatório']" />
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" label="Criar" />
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
import { api } from 'boot/axios'
import { useClustersStore } from 'stores/clusters'
import { useTeachersStore } from 'stores/teachers'
import { useAcademicYearsStore } from 'stores/academicYears'

const $q = useQuasar()
const clustersStore = useClustersStore()
const teachersStore = useTeachersStore()
const yearsStore = useAcademicYearsStore()

const DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
const dayOptions = DAYS.map((d, i) => ({ label: d, value: i }))

const search = ref('')
const types = ref<{ id: number; cluster_id: number; name: string; color: string }[]>([])
const assignments = ref<{ id: number; teacher_id: number; non_teaching_type_id: number; academic_year_id: number; day_of_week: number; slot_number: number }[]>([])
const filterTeacher = ref<number | null>(null)
const filterYear = ref<number | null>(null)

const typeDialog = ref(false)
const editingType = ref<null | { id: number }>(null)
const typeForm = ref({ cluster_id: null as number | null, name: '', color: '#e74c3c' })

const assignDialog = ref(false)
const assignForm = ref({ teacher_id: null as number | null, non_teaching_type_id: null as number | null, academic_year_id: null as number | null, day_of_week: null as number | null, slot_number: 1 })

const clusterOptions = computed(() => clustersStore.clusters.map((c) => ({ label: c.name, value: c.id })))
const teacherOptions = computed(() => teachersStore.teachers.map((t) => ({ label: t.name, value: t.id })))
const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const typeOptions = computed(() => types.value.map((t) => ({ label: t.name, value: t.id })))

function typeName(id: number) { return types.value.find((t) => t.id === id)?.name ?? '—' }

const assignCols = [
  { name: 'teacher', label: 'Professor', field: (r: { teacher_id: number }) => teachersStore.teachers.find(t => t.id === r.teacher_id)?.name ?? '—', align: 'left' as const },
  { name: 'type', label: 'Tipo', field: 'non_teaching_type_id', align: 'left' as const },
  { name: 'day', label: 'Dia', field: 'day_of_week', align: 'center' as const },
  { name: 'slot_number', label: 'Tempo', field: 'slot_number', align: 'center' as const },
  { name: 'actions', label: '', field: 'actions', align: 'center' as const },
]

async function loadTypes() {
  const { data } = await api.get('/non-teaching/types')
  types.value = data
}

async function loadAssignments() {
  const params: Record<string, number> = {}
  if (filterTeacher.value) params.teacher_id = filterTeacher.value
  if (filterYear.value) params.academic_year_id = filterYear.value
  const { data } = await api.get('/non-teaching/assignments', { params })
  assignments.value = data
}

function openTypeCreate() {
  editingType.value = null
  typeForm.value = { cluster_id: null, name: '', color: '#e74c3c' }
  typeDialog.value = true
}

function openTypeEdit(t: { id: number; cluster_id: number; name: string; color: string }) {
  editingType.value = t
  typeForm.value = { cluster_id: t.cluster_id, name: t.name, color: t.color }
  typeDialog.value = true
}

async function saveType() {
  try {
    if (editingType.value) {
      const { data } = await api.put(`/non-teaching/types/${editingType.value.id}`, typeForm.value)
      const idx = types.value.findIndex((t) => t.id === (editingType.value as { id: number }).id)
      if (idx !== -1) types.value[idx] = data
    } else {
      const { data } = await api.post('/non-teaching/types', typeForm.value)
      types.value.push(data)
    }
    typeDialog.value = false
    $q.notify({ type: 'positive', message: 'Guardado' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro' })
  }
}

async function deleteType(id: number) {
  await api.delete(`/non-teaching/types/${id}`)
  types.value = types.value.filter((t) => t.id !== id)
}

function openAssignCreate() {
  assignForm.value = { teacher_id: filterTeacher.value, non_teaching_type_id: null, academic_year_id: filterYear.value, day_of_week: null, slot_number: 1 }
  assignDialog.value = true
}

async function createAssignment() {
  try {
    const { data } = await api.post('/non-teaching/assignments', assignForm.value)
    assignments.value.push(data)
    assignDialog.value = false
    $q.notify({ type: 'positive', message: 'Criado' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro' })
  }
}

async function deleteAssignment(id: number) {
  await api.delete(`/non-teaching/assignments/${id}`)
  assignments.value = assignments.value.filter((a) => a.id !== id)
}

onMounted(async () => {
  await Promise.all([
    loadTypes(),
    teachersStore.fetchAll(),
    clustersStore.fetchAll(),
    yearsStore.fetchAll(),
  ])
  filterYear.value = yearsStore.years.find((y) => y.is_active)?.id ?? null
  if (filterYear.value) await loadAssignments()
})
</script>
