<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Horários</div>
      <q-btn color="primary" icon="add" label="Novo" @click="openCreate" />
    </div>

    <q-table :rows="store.timetables" :columns="columns" row-key="id" :loading="store.loading">
      <template #body-cell-status="props">
        <q-td :props="props">
          <q-badge :color="statusColor(props.row.status)" :label="statusLabel(props.row.status)" />
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn
            flat round dense icon="play_arrow" color="positive"
            title="Gerar"
            :loading="store.generating"
            :disable="props.row.status === 'generating'"
            @click="openGenerateDialog(props.row)"
          />
          <q-btn flat round dense icon="visibility" color="primary" :to="`/timetables/${props.row.id}`" />
          <q-btn flat round dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 400px">
        <q-card-section><div class="text-h6">Novo Horário</div></q-card-section>
        <q-card-section>
          <q-form @submit="create">
            <q-select v-model="form.academic_year_id" :options="yearOptions" label="Ano Letivo *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.name" label="Nome do horário *" :rules="[v => !!v || 'Obrigatório']" />
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" label="Criar" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <GenerateTimetableDialog v-model="showGenerateDialog" :timetable-id="generateTargetId" @started="load()" />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useTimetablesStore } from 'stores/timetables'
import { useAcademicYearsStore } from 'stores/academicYears'
import GenerateTimetableDialog from 'components/GenerateTimetableDialog.vue'

const $q = useQuasar()
const store = useTimetablesStore()
const yearsStore = useAcademicYearsStore()

const showGenerateDialog = ref(false)
const generateTargetId = ref<number | null>(null)

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'status', label: 'Estado', field: 'status', align: 'center' as const },
  { name: 'solver_status', label: 'Solver', field: 'solver_status', align: 'left' as const },
  { name: 'created_at', label: 'Criado em', field: 'created_at', align: 'left' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const dialog = ref(false)
const form = ref({ academic_year_id: null as number | null, name: '' })
const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))

function statusColor(s: string) {
  const map: Record<string, string> = { draft: 'grey', generating: 'warning', generated: 'positive', error: 'negative' }
  return map[s] ?? 'grey'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { draft: 'Rascunho', generating: 'A gerar...', generated: 'Gerado', error: 'Erro' }
  return map[s] ?? s
}

onMounted(async () => {
  await Promise.all([store.fetchAll(), yearsStore.fetchAll()])
})

async function load() {
  await store.fetchAll()
}

async function create() {
  if (!form.value.academic_year_id) return
  try {
    await store.create({ academic_year_id: form.value.academic_year_id, name: form.value.name })
    $q.notify({ type: 'positive', message: 'Horário criado' })
    dialog.value = false
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao criar' })
  }
}

function openGenerateDialog(row: { id: number }) {
  generateTargetId.value = row.id
  showGenerateDialog.value = true
}

function openCreate() {
  form.value = { academic_year_id: null, name: '' }
  dialog.value = true
}

function confirmDelete(row: { id: number; name: string }) {
  $q.dialog({
    title: 'Confirmar eliminação',
    message: `Eliminar "${row.name}"?`,
    ok: { label: 'Eliminar', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    await store.remove(row.id)
    $q.notify({ type: 'positive', message: 'Eliminado' })
  })
}
</script>
