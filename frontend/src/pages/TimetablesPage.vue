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
      <template #body-cell-solver_status="props">
        <q-td :props="props">
          <template v-if="props.row.status === 'error' && props.row.solver_status">
            <span class="text-negative text-caption" style="max-width:260px;display:inline-block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;vertical-align:middle">
              {{ props.row.solver_status.split('\n')[0] }}
            </span>
            <q-btn v-if="props.row.solver_status.includes('\n')" flat round dense size="xs" icon="info" color="negative" class="q-ml-xs">
              <q-tooltip max-width="420px" anchor="bottom middle" self="top middle">
                <div style="white-space:pre-wrap;font-size:0.78rem">{{ props.row.solver_status }}</div>
              </q-tooltip>
            </q-btn>
          </template>
          <span v-else class="text-caption text-grey-6">{{ props.row.solver_status }}</span>
        </q-td>
      </template>
      <template #body-cell-updated_at="props">
        <q-td :props="props">
          <span class="text-caption">{{ formatDateTime(props.row.updated_at) }}</span>
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <div class="row no-wrap q-gutter-xs">
            <q-btn unelevated size="sm" color="positive" icon="play_arrow" label="Gerar"
              :loading="store.generating"
              :disable="props.row.status === 'generating'"
              @click="openGenerateDialog(props.row)"
            />
            <q-btn unelevated size="sm" color="primary" icon="table_chart" label="Ver Horário"
              :to="`/timetables/${props.row.id}`"
            />
            <q-btn
              v-if="props.row.status === 'generating' || props.row.generation_log"
              unelevated size="sm" color="indigo-6" icon="terminal" label="Log"
              @click="openLog(props.row)"
            />
            <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar"
              @click="confirmDelete(props.row)"
            />
          </div>
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

    <GenerateTimetableDialog v-model="showGenerateDialog" :timetable-id="generateTargetId" @started="onGenerationStarted" />

    <!-- Generation log dialog -->
    <q-dialog v-model="showLogDialog" @hide="stopLogPolling">
      <q-card style="min-width: 560px; max-width: 720px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon name="terminal" class="q-mr-sm" />
            Log de Geração
            <q-spinner v-if="logTimetable?.status === 'generating'" size="18px" color="primary" class="q-ml-sm" />
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <pre class="log-output">{{ logContent || '(sem log disponível)' }}</pre>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useQuasar } from 'quasar'
import { useTimetablesStore } from 'stores/timetables'
import { useAcademicYearsStore } from 'stores/academicYears'
import GenerateTimetableDialog from 'components/GenerateTimetableDialog.vue'

const $q = useQuasar()
const store = useTimetablesStore()
const yearsStore = useAcademicYearsStore()

const showLogDialog = ref(false)
const logTimetable = ref<{ id: number; status: string; generation_log?: string | null } | null>(null)
const logContent = ref('')
let logPollInterval: ReturnType<typeof setInterval> | null = null

const showGenerateDialog = ref(false)
const generateTargetId = ref<number | null>(null)

function openLog(row: { id: number; status: string; generation_log?: string | null }) {
  logTimetable.value = row
  logContent.value = row.generation_log || ''
  showLogDialog.value = true
  if (row.status === 'generating') {
    startLogPolling(row.id)
  }
}

function startLogPolling(id: number) {
  stopLogPolling()
  logPollInterval = setInterval(async () => {
    await store.fetchAll()
    const updated = store.timetables.find((t) => t.id === id)
    if (updated) {
      logTimetable.value = updated
      logContent.value = updated.generation_log || ''
      if (updated.status !== 'generating') {
        stopLogPolling()
      }
    }
  }, 3000)
}

function stopLogPolling() {
  if (logPollInterval) {
    clearInterval(logPollInterval)
    logPollInterval = null
  }
}

onUnmounted(stopLogPolling)

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'status', label: 'Estado', field: 'status', align: 'center' as const },
  { name: 'solver_status', label: 'Solver', field: 'solver_status', align: 'left' as const },
  { name: 'updated_at', label: 'Última atualização', field: 'updated_at', align: 'left' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

function formatDateTime(iso: string | undefined | null): string {
  if (!iso) return '—'
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z')
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString('pt-PT', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

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

async function onGenerationStarted() {
  await load()
  if (generateTargetId.value) {
    const target = store.timetables.find((t) => t.id === generateTargetId.value)
    if (target) openLog(target)
  }
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

<style scoped>
.log-output {
  font-family: monospace;
  font-size: 0.8rem;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  min-height: 120px;
  max-height: 420px;
  overflow-y: auto;
}
</style>
