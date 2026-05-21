<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Tempos Letivos</div>
    </div>

    <q-card class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-sm-5">
            <q-select v-model="selectedYear" :options="yearOptions" label="Ano Letivo" emit-value map-options @update:model-value="loadSlots" />
          </div>
          <div class="col-12 col-sm-5">
            <q-select v-model="selectedSchool" :options="schoolOptions" label="Escola (sem seleção = globais)" emit-value map-options clearable @update:model-value="loadSlots" />
          </div>
          <div class="col-12 col-sm-2">
            <q-btn color="teal-7" icon="content_copy" label="Copiar de..." unelevated @click="openCopyDialog" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Warning: school has no slots configured -->
    <q-banner v-if="selectedSchool && slots.length === 0 && !loading" rounded class="bg-orange-1 text-orange-9 q-mb-md">
      <template #avatar><q-icon name="warning" color="orange-7" /></template>
      <div>
        <strong>A escola <em>{{ selectedSchoolName }}</em> não tem tempos letivos próprios configurados.</strong><br>
        O motor de geração usará os tempos globais ({{ globalSlotCount }} tempo(s) letivo(s) — pode ser insuficiente).
        <br>Use <strong>Copiar de...</strong> para copiar os tempos de outra escola, ou adicione manualmente abaixo.
      </div>
    </q-banner>

    <!-- Info: viewing global slots -->
    <q-banner v-if="!selectedSchool && !loading" rounded class="bg-blue-1 text-blue-9 q-mb-md">
      <template #avatar><q-icon name="info" color="blue-7" /></template>
      <div>
        A mostrar os <strong>tempos globais</strong> — aplicados a todas as escolas que não tenham tempos próprios configurados.
        Use <strong>Copiar de...</strong> para preencher os tempos globais a partir de uma escola específica.
      </div>
    </q-banner>

    <div class="row items-center q-mb-sm">
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
    </div>

    <q-tabs v-model="activeDay" dense class="q-mb-md">
      <q-tab v-for="(day, i) in DAYS" :key="i" :name="i" :label="day">
        <q-badge v-if="slotsForDay(i).length" color="teal" floating>{{ slotsForDay(i).length }}</q-badge>
      </q-tab>
    </q-tabs>

    <q-tab-panels v-model="activeDay" animated>
      <q-tab-panel v-for="(day, dayIdx) in DAYS" :key="dayIdx" :name="dayIdx">
        <q-table
          :rows="slotsForDay(dayIdx)"
          :columns="slotColumns"
          row-key="id"
          flat
          dense
          :loading="loading"
          :filter="search"
          sort-by="slot_number"
        >
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn unelevated size="sm" color="negative" icon="delete" @click="deleteSlot(props.row.id)" />
            </q-td>
          </template>
          <template #no-data>
            <div class="text-grey-6 text-caption q-pa-sm">Sem tempos para este dia.</div>
          </template>
        </q-table>

        <div class="row q-gutter-sm q-mt-sm">
          <q-btn color="primary" icon="add" label="Adicionar tempo" @click="openAdd(dayIdx)" />
          <q-btn
            v-if="slotsForDay(dayIdx).length > 0"
            color="indigo-6" icon="content_copy" label="Replicar para outros dias"
            outline
            @click="openReplicateDialog(dayIdx)"
          />
        </div>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Add slot dialog -->
    <q-dialog v-model="addDialog">
      <q-card style="min-width: 350px">
        <q-card-section><div class="text-h6">Novo Tempo Letivo</div></q-card-section>
        <q-card-section>
          <q-form @submit="addSlot">
            <q-input v-model.number="newSlot.slot_number" label="Nº do tempo *" type="number" min="1" :rules="[v => v > 0 || 'Obrigatório']" />
            <q-input v-model="newSlot.start_time" label="Hora início *" type="time" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="newSlot.end_time" label="Hora fim *" type="time" :rules="[v => !!v || 'Obrigatório']" />
            <q-checkbox v-model="newSlot.is_break" label="Intervalo" />
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" label="Adicionar" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Copy dialog -->
    <q-dialog v-model="copyDialog" persistent>
      <q-card style="min-width: 420px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6"><q-icon name="content_copy" class="q-mr-sm" />Copiar tempos letivos</div>
          <q-space /><q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <p class="text-body2 q-mb-md">
            Copia os tempos de uma escola para
            <strong>{{ selectedSchool ? selectedSchoolName : 'tempos globais (todas as escolas)' }}</strong>.
          </p>
          <q-select
            v-model="copySourceId"
            :options="copySourceOptions"
            label="Copiar de *"
            emit-value map-options
            @update:model-value="loadCopyPreview"
          />
          <div v-if="copyPreview.length > 0" class="q-mt-sm">
            <q-chip dense color="teal" text-color="white" icon="schedule">
              {{ copyPreview.length }} tempos ({{ copyPreview.filter(s => !s.is_break).length }} letivos + {{ copyPreview.filter(s => s.is_break).length }} intervalos)
            </q-chip>
          </div>
          <div v-if="slots.length > 0" class="q-mt-sm">
            <q-checkbox v-model="copyReplace" label="Apagar tempos existentes antes de copiar" color="negative" />
          </div>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn
            color="teal-7" icon="content_copy" label="Copiar"
            :loading="copying"
            :disable="!copySourceId || copyPreview.length === 0"
            @click="executeCopy"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Replicate dialog -->
    <q-dialog v-model="replicateDialog" persistent>
      <q-card style="min-width: 380px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6"><q-icon name="content_copy" class="q-mr-sm" />Replicar para outros dias</div>
          <q-space /><q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <p class="text-body2 q-mb-xs">
            Copia os {{ slotsForDay(replicateSourceDay).length }} tempos da
            <strong>{{ DAYS[replicateSourceDay] }}-feira</strong> para:
          </p>
          <div class="row q-gutter-sm q-mb-md">
            <q-btn flat dense size="sm" label="Todos" color="indigo-6"
              @click="replicateTargetDays = DAYS.map((_, i) => i).filter(i => i !== replicateSourceDay)" />
            <q-btn flat dense size="sm" label="Nenhum" color="grey-6"
              @click="replicateTargetDays = []" />
          </div>
          <div class="column q-gutter-xs">
            <q-checkbox
              v-for="(day, i) in DAYS" :key="i"
              v-if="i !== replicateSourceDay"
              :model-value="replicateTargetDays.includes(i)"
              :label="day + (slotsForDay(i).length ? ` (${slotsForDay(i).length} tempos existentes)` : '')"
              @update:model-value="(v) => { if (v) replicateTargetDays.push(i); else replicateTargetDays = replicateTargetDays.filter(d => d !== i) }"
            />
          </div>
          <q-checkbox
            v-if="replicateTargetDays.some(d => slotsForDay(d).length > 0)"
            v-model="replicateReplace"
            class="q-mt-md"
            label="Substituir tempos existentes nos dias selecionados"
            color="negative"
          />
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn
            color="indigo-6" icon="content_copy" label="Replicar"
            :loading="replicating"
            :disable="replicateTargetDays.length === 0"
            @click="executeReplicate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useSchoolsStore } from 'stores/schools'

type SlotRow = { id: number; day_of_week: number; slot_number: number; start_time: string; end_time: string; is_break: boolean; school_id: number | null }

const $q = useQuasar()
const yearsStore = useAcademicYearsStore()
const schoolsStore = useSchoolsStore()

const DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
const search = ref('')
const activeDay = ref(0)
const selectedYear = ref<number | null>(null)
const selectedSchool = ref<number | null>(null)
const slots = ref<SlotRow[]>([])
const loading = ref(false)
const addDialog = ref(false)
const newSlot = ref({ slot_number: 1, start_time: '08:00', end_time: '08:50', is_break: false, day_of_week: 0 })

// Copy dialog state
const copyDialog = ref(false)
const copySourceId = ref<number | null>(null)  // null = global
const copyPreview = ref<SlotRow[]>([])
const copyReplace = ref(true)
const copying = ref(false)
const globalSlotCount = ref(0)

// Replicate dialog state
const replicateDialog = ref(false)
const replicateSourceDay = ref(0)
const replicateTargetDays = ref<number[]>([])
const replicateReplace = ref(true)
const replicating = ref(false)

const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const schoolOptions = computed(() => schoolsStore.schools.map((s) => ({ label: s.name, value: s.id })))

const selectedSchoolName = computed(() =>
  schoolsStore.schools.find((s) => s.id === selectedSchool.value)?.name ?? '—'
)

// Copy source options: other schools; "globais" only when we're viewing a specific school
const GLOBAL_SOURCE = -1
const copySourceOptions = computed(() => {
  const others = schoolsStore.schools
    .filter((s) => s.id !== selectedSchool.value)
    .map((s) => ({ label: s.name, value: s.id }))
  if (selectedSchool.value) {
    // can also copy from global
    return [{ label: 'Tempos globais (sem escola específica)', value: GLOBAL_SOURCE }, ...others]
  }
  // viewing global: can only copy from specific schools
  return others
})

const slotColumns = [
  { name: 'slot_number', label: 'Nº', field: 'slot_number', align: 'center' as const, sortable: true },
  { name: 'start_time', label: 'Início', field: 'start_time', align: 'center' as const },
  { name: 'end_time', label: 'Fim', field: 'end_time', align: 'center' as const },
  { name: 'is_break', label: 'Intervalo', field: (r: SlotRow) => r.is_break ? 'Sim' : 'Não', align: 'center' as const },
  { name: 'actions', label: '', field: 'actions', align: 'center' as const },
]

function slotsForDay(day: number) {
  return slots.value.filter((s) => s.day_of_week === day).sort((a, b) => a.slot_number - b.slot_number)
}

async function loadSlots() {
  if (!selectedYear.value) return
  loading.value = true
  try {
    const params: Record<string, number> = { academic_year_id: selectedYear.value }
    if (selectedSchool.value) params.school_id = selectedSchool.value
    const { data } = await api.get('/time-slots', { params })
    slots.value = data

    // Also load global count (for the warning banner)
    if (selectedSchool.value) {
      const { data: gd } = await api.get('/time-slots', { params: { academic_year_id: selectedYear.value } })
      const globalOnly = (gd as SlotRow[]).filter(r => r.school_id === null && !r.is_break)
      globalSlotCount.value = globalOnly.length
    }
  } finally {
    loading.value = false
  }
}

function openAdd(day: number) {
  newSlot.value = { slot_number: slotsForDay(day).length + 1, start_time: '08:00', end_time: '08:50', is_break: false, day_of_week: day }
  addDialog.value = true
}

async function addSlot() {
  if (!selectedYear.value) return
  try {
    const payload = {
      academic_year_id: selectedYear.value,
      school_id: selectedSchool.value || null,
      ...newSlot.value,
    }
    const { data } = await api.post('/time-slots', payload)
    slots.value.push(data)
    addDialog.value = false
    $q.notify({ type: 'positive', message: 'Tempo adicionado' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao adicionar' })
  }
}

async function deleteSlot(id: number) {
  await api.delete(`/time-slots/${id}`)
  slots.value = slots.value.filter((s) => s.id !== id)
  $q.notify({ type: 'positive', message: 'Eliminado' })
}

function openCopyDialog() {
  copySourceId.value = null
  copyPreview.value = []
  copyReplace.value = slots.value.length > 0
  copyDialog.value = true
}

async function loadCopyPreview() {
  if (!selectedYear.value || copySourceId.value === null || copySourceId.value === undefined) {
    copyPreview.value = []
    return
  }
  const params: Record<string, number> = { academic_year_id: selectedYear.value }
  if (copySourceId.value !== GLOBAL_SOURCE) params.school_id = copySourceId.value
  const { data } = await api.get('/time-slots', { params })
  if (copySourceId.value === GLOBAL_SOURCE) {
    // global source: only rows without school
    copyPreview.value = (data as SlotRow[]).filter(r => r.school_id === null)
  } else {
    copyPreview.value = data as SlotRow[]
  }
}

async function executeCopy() {
  if (!selectedYear.value || copyPreview.value.length === 0) return
  copying.value = true
  try {
    // Delete existing slots for target (school-specific or global) if requested
    if (copyReplace.value && slots.value.length > 0) {
      await Promise.all(slots.value.map((s) => api.delete(`/time-slots/${s.id}`)))
      slots.value = []
    }

    // school_id null = copy to global; specific school = copy to that school
    const targetSchoolId = selectedSchool.value ?? null
    const payload = copyPreview.value.map((src) => ({
      academic_year_id: selectedYear.value,
      school_id: targetSchoolId,
      day_of_week: src.day_of_week,
      slot_number: src.slot_number,
      start_time: src.start_time,
      end_time: src.end_time,
      is_break: src.is_break,
    }))
    const { data: created } = await api.post('/time-slots/bulk', payload)
    slots.value = [...slots.value, ...(created as SlotRow[])]
    copyDialog.value = false
    const dest = selectedSchool.value ? selectedSchoolName.value : 'tempos globais'
    $q.notify({ type: 'positive', message: `${(created as SlotRow[]).length} tempos copiados para ${dest}` })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao copiar tempos' })
  } finally {
    copying.value = false
  }
}

function openReplicateDialog(sourceDay: number) {
  replicateSourceDay.value = sourceDay
  // Pre-select all other days that don't yet have slots
  const empty = DAYS.map((_, i) => i).filter(i => i !== sourceDay && slotsForDay(i).length === 0)
  replicateTargetDays.value = empty.length > 0 ? empty : DAYS.map((_, i) => i).filter(i => i !== sourceDay)
  replicateReplace.value = true
  replicateDialog.value = true
}

async function executeReplicate() {
  if (!selectedYear.value || replicateTargetDays.value.length === 0) return
  replicating.value = true
  try {
    const sourceSlots = slotsForDay(replicateSourceDay.value)

    // Delete existing slots on target days if requested
    if (replicateReplace.value) {
      const toDelete = slots.value.filter(s => replicateTargetDays.value.includes(s.day_of_week))
      if (toDelete.length > 0) {
        await Promise.all(toDelete.map(s => api.delete(`/time-slots/${s.id}`)))
        slots.value = slots.value.filter(s => !replicateTargetDays.value.includes(s.day_of_week))
      }
    }

    // Bulk-create slots for all target days
    const payload = replicateTargetDays.value.flatMap(targetDay =>
      sourceSlots.map(src => ({
        academic_year_id: selectedYear.value,
        school_id: selectedSchool.value ?? null,
        day_of_week: targetDay,
        slot_number: src.slot_number,
        start_time: src.start_time,
        end_time: src.end_time,
        is_break: src.is_break,
      }))
    )
    const { data: created } = await api.post('/time-slots/bulk', payload)
    slots.value = [...slots.value, ...(created as SlotRow[])]
    replicateDialog.value = false
    const daysLabel = replicateTargetDays.value.map(d => DAYS[d]).join(', ')
    $q.notify({ type: 'positive', message: `${(created as SlotRow[]).length} tempos criados para ${daysLabel}` })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao replicar tempos' })
  } finally {
    replicating.value = false
  }
}

onMounted(async () => {
  await Promise.all([yearsStore.fetchAll(), schoolsStore.fetchAll()])
  if (yearsStore.years.length > 0) {
    const active = yearsStore.years.find((y) => y.is_active) || yearsStore.years[0]
    selectedYear.value = active.id
    await loadSlots()
  }
})
</script>
