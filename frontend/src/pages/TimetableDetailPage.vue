<template>
  <q-page padding>

    <!-- Header row -->
    <div class="row items-center q-mb-md q-gutter-sm">
      <q-btn unelevated icon="arrow_back" label="Voltar" :to="'/timetables'" />
      <div class="text-h5 col">{{ timetable?.name }}</div>
      <q-badge v-if="timetable" :color="statusColor(timetable.status)" :label="statusLabel(timetable.status)" />
    </div>

    <!-- Solver status / error banner -->
    <q-banner
      v-if="timetable?.solver_status"
      :class="timetable.status === 'error' ? ($q.dark.isActive ? 'bg-red-10' : 'bg-red-1') : ($q.dark.isActive ? 'bg-grey-9' : 'bg-grey-2')"
      class="q-mb-md rounded-borders"
      dense
    >
      <template #avatar>
        <q-icon
          :name="timetable.status === 'error' ? 'error' : 'info'"
          :color="timetable.status === 'error' ? 'negative' : 'grey-7'"
        />
      </template>
      <div class="text-caption" style="white-space:pre-wrap">{{ timetable.solver_status }}</div>
      <template #action v-if="timetable.generation_log">
        <q-btn flat dense size="sm" :label="showLog ? 'Ocultar log' : 'Ver log'" @click="showLog = !showLog" />
      </template>
    </q-banner>
    <q-slide-transition>
      <q-card v-if="showLog && timetable?.generation_log" flat bordered class="q-mb-md">
        <q-card-section class="q-pa-sm">
          <pre class="text-caption q-ma-none" style="white-space:pre-wrap;max-height:180px;overflow-y:auto">{{ timetable.generation_log }}</pre>
        </q-card-section>
      </q-card>
    </q-slide-transition>

    <!-- Toolbar -->
    <q-card class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-sm items-center flex-wrap">

          <!-- View mode toggle -->
          <div class="col-auto">
            <q-btn-toggle
              v-model="viewMode"
              :options="[
                { label: 'Turma', value: 'class' },
                { label: 'Professor', value: 'teacher' },
                { label: 'Sala', value: 'room' },
                { label: 'Tripla Vista', value: 'triple', icon: 'view_column' },
              ]"
              color="primary"
              outline
              @update:model-value="onViewChange"
            />
          </div>

          <!-- Single entity selector (hidden in triple mode) -->
          <div class="col-sm-3" v-if="viewMode !== 'triple'">
            <q-select
              v-model="selectedEntity"
              :options="entityOptions"
              :label="entityLabel"
              emit-value map-options dense
              @update:model-value="loadSingle"
            />
          </div>

          <!-- Export + Locks (shown in single-view modes) -->
          <template v-if="viewMode !== 'triple'">
            <div class="col-auto">
              <q-btn-group flat>
                <q-btn flat icon="code" label="HTML" size="sm" @click="exportFile('html')" />
                <q-btn flat icon="table_chart" label="Excel" size="sm" @click="exportFile('excel')" />
                <q-btn flat icon="description" label="CSV" size="sm" @click="exportFile('csv')" />
                <q-btn flat icon="picture_as_pdf" label="PDF" size="sm" color="red-7" @click="exportFile('pdf')" />
              </q-btn-group>
            </div>
          </template>

          <div class="col-auto">
            <q-btn flat icon="lock" label="Bloqueios" color="warning" size="sm" @click="showLocksDialog = true">
              <q-tooltip>Bloquear turmas/professores para preservar o horário durante a próxima geração</q-tooltip>
            </q-btn>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- ── Single view (class / teacher / room) ─────────── -->
    <q-card v-if="viewMode !== 'triple'">
      <q-card-section v-if="loading" class="text-center q-pa-xl">
        <q-spinner size="50px" color="primary" />
        <div class="q-mt-md text-grey">A carregar...</div>
      </q-card-section>
      <q-card-section v-else-if="!selectedEntity" class="text-center text-grey q-pa-xl">
        <q-icon name="calendar_today" size="48px" color="grey-3" />
        <div class="q-mt-sm">Selecione {{ articleFor(viewMode) }} {{ entityLabel.toLowerCase() }} para ver o horário</div>
      </q-card-section>
      <q-card-section v-else-if="lessons.length === 0" class="text-center text-grey q-pa-xl">
        <q-icon name="event_busy" size="48px" color="grey-3" />
        <div class="q-mt-sm">Sem aulas agendadas</div>
      </q-card-section>
      <q-card-section v-else>
        <TimetableGrid
          :lessons="lessons"
          :slots="slots"
          :view="viewMode"
          :timetable-id="timetable?.id"
          @lesson-moved="loadSingle"
        />
      </q-card-section>
    </q-card>

    <!-- ── Triple view: class + teacher + room ──────────── -->
    <div v-else class="row q-col-gutter-md">

      <!-- Turma panel -->
      <div class="col-12 col-lg-4">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-py-sm row items-center bg-blue-1">
            <q-icon name="group" color="blue-8" class="q-mr-xs" />
            <span class="text-subtitle2 text-blue-9 col">Turma</span>
          </q-card-section>
          <q-card-section class="q-pt-sm">
            <q-select
              v-model="tripleClassId"
              :options="classOptions"
              label="Selecionar turma"
              emit-value map-options dense outlined
              @update:model-value="loadClass"
            />
          </q-card-section>
          <q-card-section v-if="loadingClass" class="text-center q-py-lg">
            <q-spinner color="blue" />
          </q-card-section>
          <q-card-section v-else-if="!tripleClassId" class="text-center text-grey q-py-md">
            <q-icon name="group" size="32px" color="grey-3" />
            <div class="text-caption q-mt-xs">Selecione uma turma</div>
          </q-card-section>
          <q-card-section v-else-if="classLessons.length === 0" class="text-center text-grey q-py-md">
            <div class="text-caption">Sem aulas</div>
          </q-card-section>
          <q-card-section v-else class="q-pt-none" style="overflow-x:auto">
            <TimetableGrid
              :lessons="classLessons"
              :slots="slots"
              view="class"
              :timetable-id="timetable?.id"
              @lesson-moved="onTripleMoved"
            />
          </q-card-section>
        </q-card>
      </div>

      <!-- Professor panel -->
      <div class="col-12 col-lg-4">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-py-sm row items-center bg-deep-orange-1">
            <q-icon name="person" color="deep-orange-8" class="q-mr-xs" />
            <span class="text-subtitle2 text-deep-orange-9 col">Professor</span>
          </q-card-section>
          <q-card-section class="q-pt-sm">
            <q-select
              v-model="tripleTeacherId"
              :options="teacherOptions"
              label="Selecionar professor"
              emit-value map-options dense outlined
              use-input input-debounce="0"
              @filter="filterTeachers"
              @update:model-value="loadTeacher"
            />
          </q-card-section>
          <q-card-section v-if="loadingTeacher" class="text-center q-py-lg">
            <q-spinner color="deep-orange" />
          </q-card-section>
          <q-card-section v-else-if="!tripleTeacherId" class="text-center text-grey q-py-md">
            <q-icon name="person" size="32px" color="grey-3" />
            <div class="text-caption q-mt-xs">Selecione um professor</div>
          </q-card-section>
          <q-card-section v-else-if="teacherLessons.length === 0" class="text-center text-grey q-py-md">
            <div class="text-caption">Sem aulas</div>
          </q-card-section>
          <q-card-section v-else class="q-pt-none" style="overflow-x:auto">
            <TimetableGrid
              :lessons="teacherLessons"
              :slots="slots"
              view="teacher"
              :timetable-id="timetable?.id"
              @lesson-moved="onTripleMoved"
            />
          </q-card-section>
        </q-card>
      </div>

      <!-- Sala panel -->
      <div class="col-12 col-lg-4">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-py-sm row items-center bg-brown-1">
            <q-icon name="meeting_room" color="brown-8" class="q-mr-xs" />
            <span class="text-subtitle2 text-brown-9 col">Sala</span>
          </q-card-section>
          <q-card-section class="q-pt-sm">
            <q-select
              v-model="tripleRoomId"
              :options="roomOptions"
              label="Selecionar sala"
              emit-value map-options dense outlined
              @update:model-value="loadRoom"
            />
          </q-card-section>
          <q-card-section v-if="loadingRoom" class="text-center q-py-lg">
            <q-spinner color="brown" />
          </q-card-section>
          <q-card-section v-else-if="!tripleRoomId" class="text-center text-grey q-py-md">
            <q-icon name="meeting_room" size="32px" color="grey-3" />
            <div class="text-caption q-mt-xs">Selecione uma sala</div>
          </q-card-section>
          <q-card-section v-else-if="roomLessons.length === 0" class="text-center text-grey q-py-md">
            <div class="text-caption">Sem aulas</div>
          </q-card-section>
          <q-card-section v-else class="q-pt-none" style="overflow-x:auto">
            <TimetableGrid
              :lessons="roomLessons"
              :slots="slots"
              view="room"
              :timetable-id="timetable?.id"
              @lesson-moved="onTripleMoved"
            />
          </q-card-section>
        </q-card>
      </div>

    </div>

    <TimetableLocksDialog
      v-model="showLocksDialog"
      :timetable-id="timetable?.id ?? null"
      :teachers="teachersStore.teachers"
      :classes="classesStore.classes"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useTimetablesStore, type ScheduledLesson, type TimetableDetail } from 'stores/timetables'
import { useClassesStore } from 'stores/classes'
import { useTeachersStore } from 'stores/teachers'
import { api } from 'boot/axios'
import TimetableGrid from 'components/TimetableGrid.vue'
import TimetableLocksDialog from 'components/TimetableLocksDialog.vue'

const route = useRoute()
const $q = useQuasar()
const store = useTimetablesStore()
const classesStore = useClassesStore()
const teachersStore = useTeachersStore()

// ── Core state ──────────────────────────────────────────
const timetable = ref<TimetableDetail | null>(null)
const slots = ref<{ slot_number: number; start_time?: string; end_time?: string }[]>([])
const rooms = ref<{ id: number; name: string }[]>([])
const showLocksDialog = ref(false)
const showLog = ref(false)

// ── Single-view state ───────────────────────────────────
const viewMode = ref<'class' | 'teacher' | 'room' | 'triple'>('class')
const selectedEntity = ref<number | null>(null)
const lessons = ref<ScheduledLesson[]>([])
const loading = ref(false)

// ── Triple-view state ───────────────────────────────────
const tripleClassId = ref<number | null>(null)
const tripleTeacherId = ref<number | null>(null)
const tripleRoomId = ref<number | null>(null)
const classLessons = ref<ScheduledLesson[]>([])
const teacherLessons = ref<ScheduledLesson[]>([])
const roomLessons = ref<ScheduledLesson[]>([])
const loadingClass = ref(false)
const loadingTeacher = ref(false)
const loadingRoom = ref(false)
const teacherFilterOptions = ref<{ label: string; value: number }[]>([])

// ── Options ─────────────────────────────────────────────
const entityLabel = computed(() => {
  if (viewMode.value === 'class') return 'Turma'
  if (viewMode.value === 'teacher') return 'Professor'
  return 'Sala'
})

const entityOptions = computed(() => {
  if (viewMode.value === 'class') return classOptions.value
  if (viewMode.value === 'teacher') return teacherOptions.value
  return roomOptions.value
})

const classOptions = computed(() =>
  classesStore.classes.map((c) => ({ label: c.name, value: c.id }))
)
const teacherOptions = ref<{ label: string; value: number }[]>([])
const roomOptions = computed(() =>
  rooms.value.map((r) => ({ label: r.name, value: r.id }))
)

// ── Helpers ─────────────────────────────────────────────
function statusColor(s: string) {
  return ({ draft: 'grey', generating: 'warning', generated: 'positive', error: 'negative' })[s] ?? 'grey'
}
function statusLabel(s: string) {
  return ({ draft: 'Rascunho', generating: 'A gerar...', generated: 'Gerado', error: 'Erro' })[s] ?? s
}
function articleFor(mode: string) {
  if (mode === 'class') return 'uma'
  if (mode === 'teacher') return 'um'
  return 'uma'
}

function filterTeachers(val: string, update: (fn: () => void) => void) {
  update(() => {
    const txt = val.toLowerCase()
    teacherOptions.value = teachersStore.teachers
      .filter((t) => t.name.toLowerCase().includes(txt))
      .map((t) => ({ label: t.name, value: t.id }))
  })
}

// ── Single-view loaders ─────────────────────────────────
async function loadSingle() {
  if (!timetable.value || !selectedEntity.value) { lessons.value = []; return }
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

// ── Triple-view loaders ─────────────────────────────────
async function loadClass() {
  if (!timetable.value || !tripleClassId.value) { classLessons.value = []; return }
  loadingClass.value = true
  try { classLessons.value = await store.fetchByClass(timetable.value.id, tripleClassId.value) }
  finally { loadingClass.value = false }
}

async function loadTeacher() {
  if (!timetable.value || !tripleTeacherId.value) { teacherLessons.value = []; return }
  loadingTeacher.value = true
  try { teacherLessons.value = await store.fetchByTeacher(timetable.value.id, tripleTeacherId.value) }
  finally { loadingTeacher.value = false }
}

async function loadRoom() {
  if (!timetable.value || !tripleRoomId.value) { roomLessons.value = []; return }
  loadingRoom.value = true
  try { roomLessons.value = await store.fetchByRoom(timetable.value.id, tripleRoomId.value) }
  finally { loadingRoom.value = false }
}

async function onTripleMoved() {
  // Reload all three panels in parallel after any move
  await Promise.all([loadClass(), loadTeacher(), loadRoom()])
}

// ── View mode change ────────────────────────────────────
function onViewChange() {
  if (viewMode.value !== 'triple') {
    selectedEntity.value = null
    lessons.value = []
  }
}

watch(viewMode, (newMode) => {
  if (newMode !== 'triple') {
    selectedEntity.value = null
    lessons.value = []
  }
})

// ── Export ──────────────────────────────────────────────
async function exportFile(type: 'html' | 'excel' | 'csv' | 'pdf') {
  if (!timetable.value) return
  const exportType = type === 'pdf' ? 'html' : type
  const url = `/api/v1/timetables/${timetable.value.id}/export/${exportType}?view=${viewMode.value}${selectedEntity.value ? `&entity_id=${selectedEntity.value}` : ''}`
  const token = localStorage.getItem('token')
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) return
  const blob = await res.blob()
  const blobUrl = URL.createObjectURL(blob)
  if (type === 'pdf') {
    const win = window.open(blobUrl, '_blank')
    if (win) win.onload = () => win.print()
  } else {
    const ext = type === 'excel' ? 'xlsx' : type
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = `horario_${timetable.value.id}.${ext}`
    a.click()
    URL.revokeObjectURL(blobUrl)
  }
}

// ── Mount ────────────────────────────────────────────────
onMounted(async () => {
  const id = parseInt(route.params.id as string)
  timetable.value = await store.fetchDetail(id)

  if (timetable.value) {
    const [slotsRes, roomsRes] = await Promise.all([
      api.get('/time-slots', { params: { academic_year_id: timetable.value.academic_year_id } }),
      api.get('/rooms'),
    ])
    slots.value = slotsRes.data
    rooms.value = roomsRes.data

    await Promise.all([classesStore.fetchAll(), teachersStore.fetchAll()])
    teacherOptions.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
  }
})
</script>
