<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Tempos Letivos</div>
    </div>

    <q-card class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-sm-6">
            <q-select v-model="selectedYear" :options="yearOptions" label="Ano Letivo" emit-value map-options @update:model-value="loadSlots" />
          </div>
          <div class="col-12 col-sm-6">
            <q-select v-model="selectedSchool" :options="schoolOptions" label="Escola (ou todas)" emit-value map-options clearable @update:model-value="loadSlots" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-tabs v-model="activeDay" dense class="q-mb-md">
      <q-tab v-for="(day, i) in DAYS" :key="i" :name="i" :label="day" />
    </q-tabs>

    <q-tab-panels v-model="activeDay" animated>
      <q-tab-panel v-for="(day, dayIdx) in DAYS" :key="dayIdx" :name="dayIdx">
        <q-table
          :rows="slotsForDay(dayIdx)"
          :columns="slotColumns"
          row-key="id"
          flat
          dense
        >
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn flat round dense icon="delete" color="negative" @click="deleteSlot(props.row.id)" />
            </q-td>
          </template>
        </q-table>

        <q-btn class="q-mt-sm" color="primary" icon="add" label="Adicionar tempo" @click="openAdd(dayIdx)" />
      </q-tab-panel>
    </q-tab-panels>

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
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useSchoolsStore } from 'stores/schools'

const $q = useQuasar()
const yearsStore = useAcademicYearsStore()
const schoolsStore = useSchoolsStore()

const DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
const activeDay = ref(0)
const selectedYear = ref<number | null>(null)
const selectedSchool = ref<number | null>(null)
const slots = ref<{ id: number; day_of_week: number; slot_number: number; start_time: string; end_time: string; is_break: boolean }[]>([])
const addDialog = ref(false)
const newSlot = ref({ slot_number: 1, start_time: '08:00', end_time: '08:50', is_break: false, day_of_week: 0 })

const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))
const schoolOptions = computed(() => schoolsStore.schools.map((s) => ({ label: s.name, value: s.id })))

const slotColumns = [
  { name: 'slot_number', label: 'Nº', field: 'slot_number', align: 'center' as const },
  { name: 'start_time', label: 'Início', field: 'start_time', align: 'center' as const },
  { name: 'end_time', label: 'Fim', field: 'end_time', align: 'center' as const },
  { name: 'is_break', label: 'Intervalo', field: (r: { is_break: boolean }) => r.is_break ? 'Sim' : 'Não', align: 'center' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

function slotsForDay(day: number) {
  return slots.value.filter((s) => s.day_of_week === day).sort((a, b) => a.slot_number - b.slot_number)
}

async function loadSlots() {
  if (!selectedYear.value) return
  const params: Record<string, number> = { academic_year_id: selectedYear.value }
  if (selectedSchool.value) params.school_id = selectedSchool.value
  const { data } = await api.get('/time-slots', { params })
  slots.value = data
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

onMounted(async () => {
  await Promise.all([yearsStore.fetchAll(), schoolsStore.fetchAll()])
  if (yearsStore.years.length > 0) {
    const active = yearsStore.years.find((y) => y.is_active) || yearsStore.years[0]
    selectedYear.value = active.id
    await loadSlots()
  }
})
</script>
