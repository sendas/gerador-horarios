<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <q-btn flat round dense icon="arrow_back" :to="'/timetables'" class="q-mr-sm" />
      <div class="text-h5 col">{{ timetable?.name }}</div>
      <q-badge v-if="timetable" :color="statusColor(timetable.status)" :label="statusLabel(timetable.status)" class="q-mr-sm" />
    </div>

    <q-card class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-md items-end">
          <div class="col-auto">
            <q-btn-toggle
              v-model="viewMode"
              :options="[
                { label: 'Por Turma', value: 'class' },
                { label: 'Por Professor', value: 'teacher' },
                { label: 'Por Sala', value: 'room' },
              ]"
              color="primary"
              outline
              @update:model-value="loadLessons"
            />
          </div>
          <div class="col-sm-3">
            <q-select
              v-model="selectedEntity"
              :options="entityOptions"
              :label="entityLabel"
              emit-value map-options dense
              @update:model-value="loadLessons"
            />
          </div>
          <div class="col-auto">
            <q-btn-group>
              <q-btn flat icon="code" label="HTML" @click="exportFile('html')" />
              <q-btn flat icon="table_chart" label="Excel" @click="exportFile('excel')" />
              <q-btn flat icon="description" label="CSV" @click="exportFile('csv')" />
            </q-btn-group>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card>
      <q-card-section v-if="loading" class="text-center q-pa-xl">
        <q-spinner size="50px" color="primary" />
        <div class="q-mt-md text-grey">A carregar...</div>
      </q-card-section>
      <q-card-section v-else-if="!selectedEntity" class="text-center text-grey q-pa-xl">
        Selecione uma {{ entityLabel.toLowerCase() }} para ver o horário
      </q-card-section>
      <q-card-section v-else-if="lessons.length === 0" class="text-center text-grey q-pa-xl">
        <q-icon name="calendar_today" size="64px" color="grey-3" /><br>
        Sem aulas agendadas
      </q-card-section>
      <q-card-section v-else>
        <TimetableGrid :lessons="lessons" :slots="slots" :view="viewMode" />
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTimetablesStore, type ScheduledLesson, type TimetableDetail } from 'stores/timetables'
import { useClassesStore } from 'stores/classes'
import { useTeachersStore } from 'stores/teachers'
import { api } from 'boot/axios'
import TimetableGrid from 'components/TimetableGrid.vue'

const route = useRoute()
const store = useTimetablesStore()
const classesStore = useClassesStore()
const teachersStore = useTeachersStore()

const timetable = ref<TimetableDetail | null>(null)
const viewMode = ref<'class' | 'teacher' | 'room'>('class')
const selectedEntity = ref<number | null>(null)
const lessons = ref<ScheduledLesson[]>([])
const slots = ref<{ slot_number: number; start_time?: string; end_time?: string }[]>([])
const loading = ref(false)
const rooms = ref<{ id: number; name: string }[]>([])

const entityLabel = computed(() => {
  if (viewMode.value === 'class') return 'Turma'
  if (viewMode.value === 'teacher') return 'Professor'
  return 'Sala'
})

const entityOptions = computed(() => {
  if (viewMode.value === 'class') return classesStore.classes.map((c) => ({ label: c.name, value: c.id }))
  if (viewMode.value === 'teacher') return teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
  return rooms.value.map((r) => ({ label: r.name, value: r.id }))
})

function statusColor(s: string) {
  const map: Record<string, string> = { draft: 'grey', generating: 'warning', generated: 'positive', error: 'negative' }
  return map[s] ?? 'grey'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { draft: 'Rascunho', generating: 'A gerar...', generated: 'Gerado', error: 'Erro' }
  return map[s] ?? s
}

async function loadLessons() {
  if (!timetable.value || !selectedEntity.value) {
    lessons.value = []
    return
  }
  loading.value = true
  try {
    if (viewMode.value === 'class') {
      lessons.value = await store.fetchByClass(timetable.value.id, selectedEntity.value)
    } else if (viewMode.value === 'teacher') {
      lessons.value = await store.fetchByTeacher(timetable.value.id, selectedEntity.value)
    } else {
      lessons.value = await store.fetchByRoom(timetable.value.id, selectedEntity.value)
    }
  } finally {
    loading.value = false
  }
}

function exportFile(type: 'html' | 'excel' | 'csv') {
  if (!timetable.value) return
  const url = `/api/v1/timetables/${timetable.value.id}/export/${type}?view=${viewMode.value}${selectedEntity.value ? `&entity_id=${selectedEntity.value}` : ''}`
  window.open(url, '_blank')
}

watch(viewMode, () => {
  selectedEntity.value = null
  lessons.value = []
})

onMounted(async () => {
  const id = parseInt(route.params.id as string)
  timetable.value = await store.fetchDetail(id)

  if (timetable.value) {
    const slotsRes = await api.get('/time-slots', { params: { academic_year_id: timetable.value.academic_year_id } })
    slots.value = slotsRes.data
    const roomsRes = await api.get('/rooms')
    rooms.value = roomsRes.data
    await Promise.all([classesStore.fetchAll(), teachersStore.fetchAll()])
  }
})
</script>
