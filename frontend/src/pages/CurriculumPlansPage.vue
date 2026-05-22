<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="col">
        <div class="text-h5 text-weight-bold">
          <q-icon name="menu_book" color="deep-purple-6" class="q-mr-sm" />
          Planos Curriculares
        </div>
        <div class="text-caption text-grey-6">
          Define a carga horária por ano de escolaridade e aplica às turmas
        </div>
      </div>
    </div>

    <!-- Filters -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section class="row q-gutter-md items-end">
        <q-select
          v-model="selectedCluster"
          :options="clusters"
          option-value="id"
          option-label="name"
          emit-value
          map-options
          label="Agrupamento"
          style="min-width:220px"
          @update:model-value="onClusterChange"
        />
        <q-select
          v-model="selectedYear"
          :options="academicYears"
          option-value="id"
          option-label="name"
          emit-value
          map-options
          label="Ano Letivo"
          style="min-width:180px"
          :disable="!selectedCluster"
          @update:model-value="loadPlans"
        />
        <q-space />
        <q-btn
          icon="sync"
          label="Sincronizar das turmas"
          color="orange-8"
          outline
          :disable="!selectedCluster || !selectedYear"
          :loading="syncing"
          @click="syncFromEntries"
        >
          <q-tooltip>Preenche o plano curricular com base nas disciplinas já atribuídas às turmas</q-tooltip>
        </q-btn>
        <q-btn
          icon="content_copy"
          label="Copiar para outro ano"
          color="teal-7"
          outline
          :disable="!selectedCluster || !selectedYear"
          @click="openCopyDialog"
        />
      </q-card-section>
    </q-card>

    <div v-if="!selectedCluster || !selectedYear" class="text-center text-grey-5 q-py-xl">
      <q-icon name="menu_book" size="64px" />
      <div class="q-mt-md">Seleciona um agrupamento e ano letivo</div>
    </div>

    <template v-else>
      <!-- Year level tabs -->
      <q-card flat bordered>
        <q-tabs
          v-model="activeTab"
          dense
          align="left"
          indicator-color="deep-purple-6"
          active-color="deep-purple-6"
        >
          <q-tab
            v-for="yl in allYearLevels"
            :key="yl"
            :name="String(yl)"
            :label="`${yl}.º ano`"
          />
          <q-btn
            flat
            icon="add"
            label="Adicionar ano"
            size="sm"
            color="grey-7"
            class="q-ml-sm self-center"
            @click="addYearLevelDialog = true"
          />
        </q-tabs>

        <q-separator />

        <q-tab-panels v-model="activeTab" animated>
          <q-tab-panel
            v-for="yl in allYearLevels"
            :key="yl"
            :name="String(yl)"
            class="q-pa-none"
          >
            <div class="row items-center q-pa-md q-pb-sm">
              <div class="text-subtitle1 text-weight-medium">
                {{ yl }}.º ano — {{ plansByYL[yl]?.length || 0 }} disciplina(s)
              </div>
              <q-space />
              <q-btn
                icon="content_copy"
                label="Copiar ano"
                color="deep-purple-4"
                size="sm"
                outline
                class="q-mr-sm"
                :disable="!plansByYL[yl]?.length"
                @click="openCopyYLDialog(yl)"
              >
                <q-tooltip>Copiar disciplinas deste ano para outro ano de escolaridade</q-tooltip>
              </q-btn>
              <q-btn
                icon="playlist_add"
                label="Adicionar disciplina"
                color="deep-purple-6"
                size="sm"
                outline
                class="q-mr-sm"
                @click="openAddEntry(yl)"
              />
              <q-btn
                icon="rocket_launch"
                label="Aplicar às turmas"
                color="green-7"
                size="sm"
                @click="applyPlan(yl)"
              />
            </div>

            <q-table
              :rows="plansByYL[yl] || []"
              :columns="columns"
              row-key="id"
              flat
              dense
              :rows-per-page-options="[0]"
              hide-pagination
              separator="horizontal"
            >
              <template #body-cell-subject_name="props">
                <q-td :props="props">
                  <q-badge
                    :style="{ backgroundColor: props.row.subject_color || '#888' }"
                    class="q-mr-sm"
                    rounded
                  />
                  {{ props.row.subject_name }}
                </q-td>
              </template>

              <template #body-cell-semester="props">
                <q-td :props="props">
                  <q-badge
                    v-if="props.row.is_semestral"
                    :color="props.row.semester === 1 ? 'blue-7' : 'orange-7'"
                    :label="props.row.semester === 1 ? '1.º Sem' : '2.º Sem'"
                  />
                  <span v-else class="text-grey-5 text-caption">Anual</span>
                </q-td>
              </template>

              <template #body-cell-paired="props">
                <q-td :props="props">
                  <span v-if="props.row.paired_subject_name" class="text-caption text-positive">
                    <q-icon name="swap_horiz" size="xs" class="q-mr-xs" />{{ props.row.paired_subject_name }}
                  </span>
                  <span v-else-if="props.row.is_semestral" class="text-caption text-warning">
                    <q-icon name="warning" size="xs" class="q-mr-xs" />sem par
                  </span>
                </q-td>
              </template>

              <template #body-cell-weekly_structure="props">
                <q-td :props="props">
                  <q-chip dense size="sm" color="blue-grey-1" text-color="blue-grey-8">
                    {{ props.row.weekly_structure }}
                  </q-chip>
                </q-td>
              </template>

              <template #body-cell-actions="props">
                <q-td :props="props" auto-width>
                  <q-btn flat round icon="edit" size="sm" color="primary" @click="openEditEntry(props.row)" />
                  <q-btn flat round icon="delete" size="sm" color="negative" @click="deletePlan(props.row)" />
                </q-td>
              </template>
            </q-table>

            <div v-if="!plansByYL[yl]?.length" class="text-center text-grey-5 q-py-lg">
              Sem disciplinas definidas — clica em "Adicionar disciplina"
            </div>
          </q-tab-panel>
        </q-tab-panels>
      </q-card>
    </template>

    <!-- Add/Edit entry dialog -->
    <q-dialog v-model="entryDialog" persistent>
      <q-card style="min-width:340px;max-width:480px;width:100%;max-height:90vh;display:flex;flex-direction:column">
        <q-card-section class="bg-deep-purple-6 text-white">
          <div class="text-h6">{{ editingEntry ? 'Editar' : 'Adicionar' }} Disciplina</div>
          <div class="text-caption">{{ dialogYearLevel }}.º ano</div>
        </q-card-section>
        <q-card-section class="q-gutter-sm" style="overflow-y:auto;flex:1">
          <q-select
            v-model="entryForm.subject_id"
            :options="subjectOptions"
            option-value="id"
            option-label="name"
            emit-value
            map-options
            label="Disciplina *"
            :disable="!!editingEntry"
            @update:model-value="onSubjectSelected"
          />
          <q-input
            v-model.number="entryForm.hours_per_week"
            type="number"
            label="Horas/semana *"
            min="0.5"
            step="0.5"
          />
          <q-select
            v-model="entryForm.weekly_structure"
            :options="structureOptions"
            label="Estrutura semanal"
            emit-value
            map-options
          />
          <div class="text-caption text-grey-6">
            "2+1" = bloco de 2 + 1 aula · "1+1" = duas aulas separadas · "1+1+1" = três aulas separadas
          </div>

          <q-separator class="q-my-sm" />

          <q-checkbox v-model="entryForm.is_semestral" label="Disciplina semestral (apenas meio ano)" />

          <template v-if="entryForm.is_semestral">
            <q-select
              v-model="entryForm.semester"
              :options="semesterOptions"
              option-value="value"
              option-label="label"
              emit-value
              map-options
              label="Semestre em que ocorre *"
            />
            <q-select
              v-model="entryForm.paired_subject_id"
              :options="pairedSubjectOptions"
              option-value="id"
              option-label="name"
              emit-value
              map-options
              clearable
              label="Disciplina par (semestre oposto)"
              hint="Disciplina que ocupa o mesmo horário no outro semestre"
            />
          </template>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" @click="entryDialog = false" />
          <q-btn
            :label="editingEntry ? 'Guardar' : 'Adicionar'"
            color="deep-purple-6"
            :loading="saving"
            @click="saveEntry"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Add year level dialog -->
    <q-dialog v-model="addYearLevelDialog">
      <q-card style="min-width:280px">
        <q-card-section>
          <div class="text-h6">Adicionar Ano de Escolaridade</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model.number="newYearLevel" type="number" label="Ano (ex: 5, 6, 7...)" min="1" max="12" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" @click="addYearLevelDialog = false" />
          <q-btn label="Adicionar" color="deep-purple-6" @click="addYearLevel" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Copy year dialog -->
    <q-dialog v-model="copyDialog" persistent>
      <q-card style="min-width:380px">
        <q-card-section class="bg-teal-7 text-white">
          <div class="text-h6">Copiar Plano Curricular</div>
          <div class="text-caption">De {{ selectedYearName }} para outro ano letivo</div>
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-select
            v-model="copyTarget"
            :options="academicYears.filter(y => y.id !== selectedYear)"
            option-value="id"
            option-label="name"
            emit-value
            map-options
            label="Ano letivo de destino *"
          />
          <q-toggle v-model="copyOverwrite" label="Substituir entradas já existentes no destino" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" @click="copyDialog = false" />
          <q-btn
            label="Copiar"
            color="teal-7"
            :disable="!copyTarget"
            :loading="copying"
            @click="executeCopy"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Copy year level dialog -->
    <q-dialog v-model="copyYLDialog" persistent>
      <q-card style="min-width:380px">
        <q-card-section class="bg-deep-purple-7 text-white">
          <div class="text-h6">Copiar disciplinas do {{ copyYLFrom }}.º ano</div>
          <div class="text-caption">Para outro ano de escolaridade (mesmo ano letivo)</div>
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-select
            v-model="copyYLTarget"
            :options="copyYLTargetOptions"
            option-value="value"
            option-label="label"
            emit-value
            map-options
            label="Ano de escolaridade de destino *"
          />
          <q-toggle v-model="copyYLOverwrite" label="Substituir disciplinas já existentes no destino" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" @click="copyYLDialog = false" />
          <q-btn
            label="Copiar"
            color="deep-purple-7"
            :disable="!copyYLTarget"
            :loading="copyingYL"
            @click="executeCopyYL"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Apply result dialog -->
    <q-dialog v-model="applyResultDialog">
      <q-card style="min-width:340px">
        <q-card-section class="bg-green-7 text-white">
          <div class="text-h6">Plano Aplicado</div>
        </q-card-section>
        <q-card-section>
          <p>{{ applyResultMsg }}</p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Fechar" @click="applyResultDialog = false" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import axios from 'axios'

const $q = useQuasar()
const API = '/api/v1'

const clusters = ref<any[]>([])
const academicYears = ref<any[]>([])
const subjects = ref<any[]>([])
const plans = ref<any[]>([])

const selectedCluster = ref<number | null>(null)
const selectedYear = ref<number | null>(null)
const activeTab = ref<string>('')

const entryDialog = ref(false)
const editingEntry = ref<any>(null)
const dialogYearLevel = ref<number>(5)
const saving = ref(false)

const addYearLevelDialog = ref(false)
const newYearLevel = ref<number>(5)

const copyDialog = ref(false)
const copyTarget = ref<number | null>(null)
const copyOverwrite = ref(true)
const copying = ref(false)

const copyYLDialog = ref(false)
const copyYLFrom = ref<number>(5)
const copyYLTarget = ref<number | null>(null)
const copyYLOverwrite = ref(true)
const copyingYL = ref(false)

const applyResultDialog = ref(false)
const applyResultMsg = ref('')
const syncing = ref(false)

const entryForm = ref({
  subject_id: null as number | null,
  hours_per_week: 2,
  weekly_structure: '1+1',
  is_semestral: false,
  semester: null as number | null,
  paired_subject_id: null as number | null,
})

const structureOptions = [
  { label: '1 (uma aula)', value: '1' },
  { label: '1+1 (duas aulas separadas)', value: '1+1' },
  { label: '1+1+1 (três aulas separadas)', value: '1+1+1' },
  { label: '2 (bloco de 2)', value: '2' },
  { label: '2+1 (bloco de 2 + 1 aula)', value: '2+1' },
  { label: '2+2 (dois blocos de 2)', value: '2+2' },
  { label: '3 (bloco de 3)', value: '3' },
]

const columns = [
  { name: 'subject_name', label: 'Disciplina', field: 'subject_name', align: 'left' as const, sortable: true },
  { name: 'hours_per_week', label: 'H/semana', field: 'hours_per_week', align: 'center' as const, sortable: true },
  { name: 'weekly_structure', label: 'Estrutura', field: 'weekly_structure', align: 'center' as const },
  { name: 'semester', label: 'Semestre', field: 'semester', align: 'center' as const },
  { name: 'paired', label: 'Par semestral', field: 'paired_subject_id', align: 'left' as const },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
]

const plansByYL = computed(() => {
  const map: Record<number, any[]> = {}
  for (const p of plans.value) {
    if (!map[p.year_level]) map[p.year_level] = []
    map[p.year_level].push(p)
  }
  return map
})

const allYearLevels = computed(() => Object.keys(plansByYL.value).map(Number).sort((a, b) => a - b))

const selectedYearName = computed(() => academicYears.value.find(y => y.id === selectedYear.value)?.name || '')

const copyYLTargetOptions = computed(() =>
  Array.from({ length: 12 }, (_, i) => i + 1)
    .filter(yl => yl !== copyYLFrom.value)
    .map(yl => ({
      value: yl,
      label: allYearLevels.value.includes(yl) ? `${yl}.º ano (já tem plano)` : `${yl}.º ano`,
    }))
)

const subjectOptions = computed(() => subjects.value)

const semesterOptions = [
  { label: '1.º Semestre', value: 1 },
  { label: '2.º Semestre', value: 2 },
]

const pairedSubjectOptions = computed(() => {
  const currentId = entryForm.value.subject_id
  const yl = dialogYearLevel.value
  // subjects already in this year level that are semestral, excluding the current one
  const inYL = new Set((plansByYL.value[yl] || []).map((p: any) => p.subject_id))
  return subjects.value.filter((s: any) =>
    s.id !== currentId && (inYL.has(s.id) || s.regime === 'semestral')
  )
})

const token = () => localStorage.getItem('token') || ''
const headers = () => ({ Authorization: `Bearer ${token()}` })

onMounted(async () => {
  const [cRes, sRes] = await Promise.all([
    axios.get(`${API}/clusters`, { headers: headers() }),
    axios.get(`${API}/subjects`, { headers: headers() }),
  ])
  clusters.value = cRes.data
  subjects.value = sRes.data
  if (clusters.value.length === 1) {
    selectedCluster.value = clusters.value[0].id
    await onClusterChange()
  }
})

async function onClusterChange() {
  selectedYear.value = null
  plans.value = []
  if (!selectedCluster.value) return
  const res = await axios.get(`${API}/academic-years?cluster_id=${selectedCluster.value}`, { headers: headers() })
  academicYears.value = res.data
  if (academicYears.value.length > 0) {
    const active = academicYears.value.find((y: any) => y.is_active)
    selectedYear.value = active?.id || academicYears.value[0].id
    await loadPlans()
  }
}

async function loadPlans() {
  if (!selectedCluster.value || !selectedYear.value) return
  const res = await axios.get(`${API}/curriculum-plans?cluster_id=${selectedCluster.value}&academic_year_id=${selectedYear.value}`, { headers: headers() })
  plans.value = res.data
  if (allYearLevels.value.length && !allYearLevels.value.includes(Number(activeTab.value))) {
    activeTab.value = String(allYearLevels.value[0])
  }
}

function openAddEntry(yl: number) {
  dialogYearLevel.value = yl
  editingEntry.value = null
  entryForm.value = { subject_id: null, hours_per_week: 2, weekly_structure: '1+1', is_semestral: false, semester: null, paired_subject_id: null }
  entryDialog.value = true
}

function openEditEntry(row: any) {
  dialogYearLevel.value = row.year_level
  editingEntry.value = row
  entryForm.value = {
    subject_id: row.subject_id,
    hours_per_week: row.hours_per_week,
    weekly_structure: row.weekly_structure,
    is_semestral: !!row.is_semestral,
    semester: row.semester ?? null,
    paired_subject_id: row.paired_subject_id ?? null,
  }
  entryDialog.value = true
}

function onSubjectSelected(subjectId: number) {
  const subj = subjects.value.find((s: any) => s.id === subjectId)
  if (!subj) return
  if (subj.weekly_structure) entryForm.value.weekly_structure = subj.weekly_structure
  if (subj.regime === 'semestral') {
    entryForm.value.is_semestral = true
    if (subj.default_semester) entryForm.value.semester = subj.default_semester
    if (subj.paired_subject_id) entryForm.value.paired_subject_id = subj.paired_subject_id
  }
}

async function saveEntry() {
  if (!entryForm.value.subject_id || !entryForm.value.hours_per_week) {
    $q.notify({ type: 'warning', message: 'Preenche todos os campos obrigatórios.' })
    return
  }
  saving.value = true
  try {
    const semestralPayload = {
      is_semestral: entryForm.value.is_semestral,
      semester: entryForm.value.is_semestral ? entryForm.value.semester : null,
      paired_subject_id: entryForm.value.is_semestral ? entryForm.value.paired_subject_id : null,
    }
    if (editingEntry.value) {
      await axios.put(`${API}/curriculum-plans/${editingEntry.value.id}`, {
        hours_per_week: entryForm.value.hours_per_week,
        weekly_structure: entryForm.value.weekly_structure,
        ...semestralPayload,
      }, { headers: headers() })
    } else {
      await axios.post(`${API}/curriculum-plans`, {
        cluster_id: selectedCluster.value,
        academic_year_id: selectedYear.value,
        year_level: dialogYearLevel.value,
        subject_id: entryForm.value.subject_id,
        hours_per_week: entryForm.value.hours_per_week,
        weekly_structure: entryForm.value.weekly_structure,
        ...semestralPayload,
      }, { headers: headers() })
    }
    entryDialog.value = false
    await loadPlans()
    $q.notify({ type: 'positive', message: editingEntry.value ? 'Entrada atualizada.' : 'Disciplina adicionada.' })
  } catch (e: any) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erro ao guardar.' })
  } finally {
    saving.value = false
  }
}

async function deletePlan(row: any) {
  $q.dialog({
    title: 'Confirmar',
    message: `Remover ${row.subject_name} do ${row.year_level}.º ano?`,
    cancel: true,
  }).onOk(async () => {
    await axios.delete(`${API}/curriculum-plans/${row.id}`, { headers: headers() })
    await loadPlans()
    $q.notify({ type: 'positive', message: 'Entrada removida.' })
  })
}

function addYearLevel() {
  if (!newYearLevel.value) return
  activeTab.value = String(newYearLevel.value)
  // Add a placeholder so the tab shows — actual entry added via dialog
  addYearLevelDialog.value = false
  openAddEntry(newYearLevel.value)
}

async function applyPlan(yl: number) {
  $q.dialog({
    title: `Aplicar plano do ${yl}.º ano`,
    message: 'Criar entradas curriculares em todas as turmas deste ano de escolaridade. Entradas já existentes serão mantidas (não substituídas).',
    cancel: true,
    ok: { label: 'Aplicar', color: 'green-7' },
  }).onOk(async () => {
    try {
      const res = await axios.post(`${API}/curriculum-plans/apply`, {
        cluster_id: selectedCluster.value,
        academic_year_id: selectedYear.value,
        year_levels: [yl],
        overwrite: false,
      }, { headers: headers() })
      applyResultMsg.value = res.data.message
      applyResultDialog.value = true
    } catch (e: any) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erro ao aplicar plano.' })
    }
  })
}

async function syncFromEntries() {
  $q.dialog({
    title: 'Sincronizar plano das turmas',
    message: 'Isto vai preencher (ou atualizar) o plano curricular com base nas disciplinas já atribuídas às turmas. Entradas existentes no plano serão atualizadas. Continuar?',
    cancel: true,
    ok: { label: 'Sincronizar', color: 'orange-8' },
  }).onOk(async () => {
    syncing.value = true
    try {
      const res = await axios.post(`${API}/curriculum-plans/sync-from-entries`, {
        cluster_id: selectedCluster.value,
        academic_year_id: selectedYear.value,
        overwrite: true,
      }, { headers: headers() })
      await loadPlans()
      applyResultMsg.value = res.data.message
      applyResultDialog.value = true
    } catch (e: any) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erro ao sincronizar.' })
    } finally {
      syncing.value = false
    }
  })
}

function openCopyDialog() {
  copyTarget.value = null
  copyOverwrite.value = true
  copyDialog.value = true
}

function openCopyYLDialog(yl: number) {
  copyYLFrom.value = yl
  copyYLTarget.value = null
  copyYLOverwrite.value = true
  copyYLDialog.value = true
}

async function executeCopyYL() {
  if (!copyYLTarget.value) return
  copyingYL.value = true
  try {
    const res = await axios.post(`${API}/curriculum-plans/copy-year-level`, {
      cluster_id: selectedCluster.value,
      academic_year_id: selectedYear.value,
      from_year_level: copyYLFrom.value,
      to_year_level: copyYLTarget.value,
      overwrite: copyYLOverwrite.value,
    }, { headers: headers() })
    copyYLDialog.value = false
    activeTab.value = String(copyYLTarget.value)
    await loadPlans()
    $q.notify({ type: 'positive', message: res.data.message })
  } catch (e: any) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erro ao copiar.' })
  } finally {
    copyingYL.value = false
  }
}

async function executeCopy() {
  if (!copyTarget.value) return
  copying.value = true
  try {
    const res = await axios.post(`${API}/curriculum-plans/copy`, {
      cluster_id: selectedCluster.value,
      from_academic_year_id: selectedYear.value,
      to_academic_year_id: copyTarget.value,
      overwrite: copyOverwrite.value,
    }, { headers: headers() })
    copyDialog.value = false
    $q.notify({ type: 'positive', message: res.data.message })
  } catch (e: any) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erro ao copiar.' })
  } finally {
    copying.value = false
  }
}
</script>
