<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Horários</div>
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn color="orange-8" icon="fact_check" label="Verificar dados" @click="openPreflight" class="q-ml-sm q-mr-sm" />
      <q-btn color="primary" icon="add" label="Novo" @click="openCreate" />
    </div>

    <!-- Active generation banner -->
    <template v-if="anyGenerating">
      <!-- Stale: process appears to have died -->
      <q-banner v-if="staleGenerating.length" rounded class="bg-negative text-white q-mb-md">
        <template #avatar><q-icon name="error" size="28px" /></template>
        <div>
          <strong>O processo de geração parece ter parado.</strong>
          O servidor não atualizou o estado há mais de 3 minutos. O serviço pode ter sido interrompido (reinício, falta de memória, etc.).
        </div>
        <template #action>
          <q-btn
            v-for="t in staleGenerating" :key="t.id"
            flat color="white" icon="cancel"
            :label="`Cancelar '${t.name}'`"
            class="q-ml-sm"
            @click="cancelGeneration(t)"
          />
        </template>
      </q-banner>
      <!-- Normal: still running -->
      <q-banner v-else rounded class="bg-warning text-dark q-mb-md">
        <template #avatar><q-spinner size="22px" color="dark" /></template>
        <strong>Geração em curso</strong> — o horário está a ser calculado em segundo plano.
        Pode fechar esta página; a lista atualiza automaticamente de 3 em 3 segundos.
      </q-banner>
    </template>

    <q-table :rows="store.timetables" :columns="columns" row-key="id" :loading="store.loading"
      :row-class="(row) => row.status === 'generating' ? 'row-generating' : ''"
      :filter="search"
      sort-by="name"
    >
      <template #body-cell-status="props">
        <q-td :props="props">
          <div class="row items-center no-wrap q-gutter-xs">
            <q-spinner v-if="props.row.status === 'generating'" size="14px" color="warning" />
            <q-badge :color="statusColor(props.row.status)" :label="statusLabel(props.row.status)" />
          </div>
        </q-td>
      </template>
      <template #body-cell-solver_status="props">
        <q-td :props="props">
          <!-- Relaxed-constraints warning (generated but with gaps/missing constraints) -->
          <template v-if="props.row.status === 'generated' && props.row.solver_status?.startsWith('⚠')">
            <q-badge color="orange-8" outline class="q-mr-xs" style="font-size:11px;vertical-align:middle">
              <q-icon name="warning" size="12px" class="q-mr-xs" />furos
            </q-badge>
            <q-btn flat round dense size="xs" icon="info" color="orange-8">
              <q-tooltip max-width="460px" anchor="bottom middle" self="top middle">
                <div style="white-space:pre-wrap;font-size:0.82rem;max-width:440px">
                  <div class="text-weight-bold q-mb-xs">{{ props.row.solver_status }}</div>
                  <div>O solver não encontrou solução sem furos dentro do tempo disponível e gerou o horário com restrições relaxadas.<br><br>
                  Para corrigir: <strong>regenere com 1h ou mais de tempo</strong> e as opções "Sem furos nos horários dos alunos" e "Alunos entram no 1.º tempo" ativadas.</div>
                </div>
              </q-tooltip>
            </q-btn>
          </template>
          <!-- Error status -->
          <template v-else-if="props.row.status === 'error' && props.row.solver_status">
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

    <!-- Preflight check dialog -->
    <q-dialog v-model="showPreflight">
      <q-card style="min-width: 560px; max-width: 780px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6"><q-icon name="fact_check" class="q-mr-sm" color="orange-8" />Verificação antes de gerar</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section v-if="preflightLoading" class="text-center q-py-xl">
          <q-spinner size="40px" color="primary" />
          <div class="q-mt-sm text-grey-6">A verificar dados...</div>
        </q-card-section>

        <q-card-section v-else-if="preflightResult">
          <!-- Result summary badge -->
          <q-banner rounded :class="preflightResult.can_generate ? 'bg-positive text-white' : 'bg-negative text-white'" class="q-mb-md">
            <template #avatar><q-icon :name="preflightResult.can_generate ? 'check_circle' : 'cancel'" /></template>
            <strong>{{ preflightResult.can_generate ? 'Dados prontos para gerar' : 'Não é possível gerar — corrija os erros abaixo' }}</strong>
            <span v-if="preflightResult.warnings.length && preflightResult.can_generate">
              (com {{ preflightResult.warnings.length }} aviso(s))
            </span>
          </q-banner>

          <!-- Errors -->
          <template v-if="preflightResult.errors.length">
            <div class="text-subtitle2 text-negative q-mb-xs"><q-icon name="error" class="q-mr-xs" />Erros (impedem a geração)</div>
            <q-list bordered separator class="q-mb-md rounded-borders">
              <q-item v-for="(e, i) in preflightResult.errors" :key="i">
                <q-item-section avatar><q-icon name="cancel" color="negative" /></q-item-section>
                <q-item-section>
                  <q-item-label>{{ e.message }}</q-item-label>
                  <q-item-label v-if="e.items?.length" caption>
                    {{ e.items.slice(0,5).join(' · ') }}{{ e.items.length > 5 ? ` + ${e.items.length - 5} mais` : '' }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side v-if="e.fix">
                  <q-btn flat size="sm" color="negative" icon="open_in_new" label="Corrigir" :to="e.fix" v-close-popup />
                </q-item-section>
              </q-item>
            </q-list>
          </template>

          <!-- Warnings -->
          <template v-if="preflightResult.warnings.length">
            <div class="text-subtitle2 text-warning q-mb-xs"><q-icon name="warning" class="q-mr-xs" />Avisos (geração possível mas incompleta)</div>
            <q-list bordered separator class="q-mb-md rounded-borders">
              <q-item v-for="(w, i) in preflightResult.warnings" :key="i">
                <q-item-section avatar><q-icon name="warning" color="warning" /></q-item-section>
                <q-item-section>
                  <q-item-label>{{ w.message }}</q-item-label>
                  <q-item-label v-if="w.items?.length" caption>
                    {{ w.items.slice(0,5).join(' · ') }}{{ w.items.length > 5 ? ` + ${w.items.length - 5} mais` : '' }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side v-if="w.fix">
                  <q-btn flat size="sm" color="warning" icon="open_in_new" label="Corrigir" :to="w.fix" v-close-popup />
                </q-item-section>
              </q-item>
            </q-list>
          </template>

          <!-- Info -->
          <template v-if="preflightResult.info.length">
            <div class="text-subtitle2 text-grey-7 q-mb-xs"><q-icon name="info" class="q-mr-xs" />Informação</div>
            <q-list bordered separator class="q-mb-md rounded-borders">
              <q-item v-for="(inf, i) in preflightResult.info" :key="i">
                <q-item-section avatar><q-icon name="check" color="positive" /></q-item-section>
                <q-item-section><q-item-label>{{ inf.message }}</q-item-label></q-item-section>
              </q-item>
            </q-list>
          </template>

          <!-- Year level selection + direct generation -->
          <template v-if="preflightResult.can_generate && preflightResult.year_level_summary?.length">
            <q-separator class="q-my-md" />
            <div class="text-subtitle2 q-mb-sm">
              <q-icon name="checklist" color="teal" class="q-mr-xs" />Selecionar anos de escolaridade a gerar
            </div>
            <div class="row q-gutter-sm q-mb-md flex-wrap">
              <q-chip
                v-for="yl in preflightResult.year_level_summary"
                :key="yl.year_level"
                clickable dense square
                :color="selectedYearLevels.has(yl.year_level)
                  ? (yl.viable ? 'teal' : 'grey-6')
                  : (yl.viable ? 'grey-3' : 'grey-2')"
                :text-color="selectedYearLevels.has(yl.year_level) ? 'white' : 'dark'"
                :icon="yl.viable ? (selectedYearLevels.has(yl.year_level) ? 'check_circle' : 'radio_button_unchecked') : 'block'"
                @click="yl.viable && toggleYearLevel(yl.year_level)"
              >
                {{ yl.year_level }}.º ano
                <q-badge
                  :color="yl.entries_with_teacher === yl.total_entries ? 'positive' : 'warning'"
                  floating>
                  {{ yl.entries_with_teacher }}/{{ yl.total_entries }}
                </q-badge>
                <q-tooltip>
                  {{ yl.total_classes }} turma(s) · {{ yl.entries_with_teacher }} de {{ yl.total_entries }} entradas com professor
                  <span v-if="!yl.viable"> — não viável</span>
                </q-tooltip>
              </q-chip>
            </div>

            <div class="row q-col-gutter-md items-end">
              <div class="col">
                <q-select
                  v-model="preflightTimetableId"
                  :options="store.timetables.filter(t => t.status !== 'generating').map(t => ({ label: t.name, value: t.id }))"
                  label="Horário a usar"
                  emit-value map-options dense outlined
                />
              </div>
              <div class="col-auto">
                <q-btn
                  color="positive" icon="play_arrow" label="Gerar selecionados"
                  unelevated
                  :disable="selectedYearLevels.size === 0 || !preflightTimetableId"
                  :loading="generatingFromPreflight"
                  @click="generateFromPreflight"
                />
              </div>
            </div>
          </template>
        </q-card-section>
      </q-card>
    </q-dialog>

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
import { useClustersStore } from 'stores/clusters'
import GenerateTimetableDialog from 'components/GenerateTimetableDialog.vue'
import { api } from 'boot/axios'

const $q = useQuasar()
const store = useTimetablesStore()
const yearsStore = useAcademicYearsStore()
const clustersStore = useClustersStore()

// Preflight check
type PreflightItem = { message: string; fix?: string; items?: string[] }
type YearLevelSummary = { year_level: number; total_classes: number; total_entries: number; entries_with_teacher: number; viable: boolean }
type PreflightResult = { errors: PreflightItem[]; warnings: PreflightItem[]; info: PreflightItem[]; can_generate: boolean; year_level_summary: YearLevelSummary[] }
const showPreflight = ref(false)
const preflightLoading = ref(false)
const preflightResult = ref<PreflightResult | null>(null)
const selectedYearLevels = ref<Set<number>>(new Set())
const preflightTimetableId = ref<number | null>(null)
const generatingFromPreflight = ref(false)

async function openPreflight() {
  showPreflight.value = true
  preflightLoading.value = true
  preflightResult.value = null
  const activeYear = yearsStore.years.find((y) => y.is_active) ?? yearsStore.years[0]
  const clusterId = clustersStore.clusters[0]?.id
  if (!activeYear || !clusterId) {
    preflightResult.value = {
      errors: [{ message: 'Sem ano letivo ativo ou agrupamento configurado.' }],
      warnings: [], info: [], can_generate: false, year_level_summary: []
    }
    preflightLoading.value = false
    return
  }
  try {
    const { data } = await api.get('/timetables/preflight-check', {
      params: { academic_year_id: activeYear.id, cluster_id: clusterId }
    })
    preflightResult.value = data
    // Pre-select all viable year levels
    selectedYearLevels.value = new Set(
      (data.year_level_summary as YearLevelSummary[]).filter((y) => y.viable).map((y) => y.year_level)
    )
    // Pre-select most recent timetable for this year
    const match = store.timetables.find((t) => t.academic_year_id === activeYear.id && t.status !== 'generating')
    preflightTimetableId.value = match?.id ?? store.timetables[0]?.id ?? null
  } catch {
    preflightResult.value = {
      errors: [{ message: 'Erro ao verificar dados. Tente novamente.' }],
      warnings: [], info: [], can_generate: false, year_level_summary: []
    }
  } finally {
    preflightLoading.value = false
  }
}

function toggleYearLevel(yl: number) {
  if (selectedYearLevels.value.has(yl)) selectedYearLevels.value.delete(yl)
  else selectedYearLevels.value.add(yl)
}

async function generateFromPreflight() {
  if (!preflightTimetableId.value) return
  generatingFromPreflight.value = true
  try {
    const yls = [...selectedYearLevels.value].sort((a, b) => a - b)
    await store.generate(preflightTimetableId.value, {
      year_levels: yls.length > 0 ? yls : null,
    })
    $q.notify({ type: 'positive', message: 'Geração iniciada em segundo plano' })
    showPreflight.value = false
    startGlobalPolling()
    const target = store.timetables.find((t) => t.id === preflightTimetableId.value)
    if (target) openLog(target)
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erro ao iniciar geração'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    generatingFromPreflight.value = false
  }
}

const anyGenerating = computed(() => store.timetables.some((t) => t.status === 'generating'))

// Generating timetables whose updated_at hasn't moved for >3 min (heartbeat is every 60s)
const STALE_MS = 3 * 60 * 1000
const now = ref(Date.now())

const staleGenerating = computed(() =>
  store.timetables.filter((t) => {
    if (t.status !== 'generating' || !t.updated_at) return false
    const ts = t.updated_at.endsWith('Z') ? t.updated_at : t.updated_at + 'Z'
    return now.value - new Date(ts).getTime() > STALE_MS
  })
)

async function cancelGeneration(t: { id: number; name: string }) {
  try {
    await store.cancelGeneration(t.id)
    stopGlobalPolling()
    $q.notify({ type: 'warning', message: `Geração de "${t.name}" cancelada` })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao cancelar' })
  }
}

const showLogDialog = ref(false)
const logTimetable = ref<{ id: number; status: string; generation_log?: string | null } | null>(null)
const logContent = ref('')
let logPollInterval: ReturnType<typeof setInterval> | null = null
let globalPollInterval: ReturnType<typeof setInterval> | null = null

function startGlobalPolling() {
  if (globalPollInterval) return
  globalPollInterval = setInterval(async () => {
    await store.fetchAll()
    if (!anyGenerating.value) stopGlobalPolling()
  }, 3000)
}

function stopGlobalPolling() {
  if (globalPollInterval) {
    clearInterval(globalPollInterval)
    globalPollInterval = null
  }
}

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

const nowInterval = setInterval(() => { now.value = Date.now() }, 15_000)
onUnmounted(() => { stopLogPolling(); stopGlobalPolling(); clearInterval(nowInterval) })

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

const search = ref('')
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
  await Promise.all([store.fetchAll(), yearsStore.fetchAll(), clustersStore.fetchAll()])
  if (anyGenerating.value) startGlobalPolling()
})

async function load() {
  await store.fetchAll()
}

async function onGenerationStarted() {
  await load()
  startGlobalPolling()
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
.row-generating {
  background: rgba(255, 193, 7, 0.08) !important;
  animation: pulse-row 2s ease-in-out infinite;
}

@keyframes pulse-row {
  0%, 100% { background-color: rgba(255, 193, 7, 0.08) !important; }
  50%       { background-color: rgba(255, 193, 7, 0.18) !important; }
}

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
