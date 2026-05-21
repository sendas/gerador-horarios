<template>
  <div>
    <div v-if="timetableId" class="text-caption text-grey q-mb-xs">
      <q-icon name="drag_indicator" size="xs" /> Arraste as aulas para as mover
    </div>

    <div :class="{ 'drag-active': !!dragging }">
      <table class="tt-table">
        <thead>
          <tr>
            <th class="tt-th tt-th--time">Hora</th>
            <th v-for="day in DAYS" :key="day" class="tt-th">{{ day }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="slot in uniqueSlots" :key="slot">
            <td class="tt-td tt-td--time">{{ slotLabel(slot) }}</td>
            <td
              v-for="(day, dayIdx) in DAYS"
              :key="dayIdx"
              class="tt-td tt-td--cell"
              :class="getCellClass(dayIdx, slot)"
              @dragover.prevent="onDragOver($event, dayIdx, slot)"
              @drop.prevent="onDrop(dayIdx, slot)"
            >
              <template v-for="group in cellGroups(dayIdx, slot)" :key="group.key">
                <!-- Paired semestral block -->
                <div
                  v-if="group.type === 'paired'"
                  class="lesson-card lesson-card--paired"
                  :draggable="false"
                >
                  <div class="paired-half" :style="halfStyle(group.s1!)">
                    <span class="paired-sem-tag">S1</span>
                    <span class="lesson-subject">{{ group.s1!.subject_name }}</span>
                    <div class="lesson-meta" v-if="view !== 'class' && group.s1!.class_name">{{ group.s1!.class_name }}</div>
                    <div class="lesson-meta" v-if="view !== 'teacher' && group.s1!.teacher_name">{{ group.s1!.teacher_name }}</div>
                    <div class="lesson-meta" v-if="view !== 'room' && group.s1!.room_name">{{ group.s1!.room_name }}</div>
                  </div>
                  <div class="paired-divider" />
                  <div class="paired-half" :style="halfStyle(group.s2!)">
                    <span class="paired-sem-tag">S2</span>
                    <span class="lesson-subject">{{ group.s2!.subject_name }}</span>
                    <div class="lesson-meta" v-if="view !== 'class' && group.s2!.class_name">{{ group.s2!.class_name }}</div>
                    <div class="lesson-meta" v-if="view !== 'teacher' && group.s2!.teacher_name">{{ group.s2!.teacher_name }}</div>
                    <div class="lesson-meta" v-if="view !== 'room' && group.s2!.room_name">{{ group.s2!.room_name }}</div>
                  </div>
                </div>

                <!-- Regular single lesson -->
                <div
                  v-else
                  class="lesson-card"
                  :class="{ 'lesson-card--dragging': dragging?.id === group.lesson!.id }"
                  :style="cardStyle(group.lesson!)"
                  :draggable="!!timetableId"
                  @dragstart.stop="onDragStart($event, group.lesson!)"
                  @dragend.stop="onDragEnd"
                >
                  <q-icon v-if="timetableId" name="drag_indicator" size="xs" class="lesson-drag-icon" />
                  <div class="lesson-subject">
                    {{ group.lesson!.subject_name }}
                    <q-badge
                      v-if="group.lesson!.is_semestral"
                      :color="group.lesson!.semester === 1 ? 'blue-7' : 'orange-7'"
                      :label="group.lesson!.semester === 1 ? 'S1' : 'S2'"
                      class="q-ml-xs"
                    />
                  </div>
                  <div class="lesson-meta" v-if="view !== 'class' && group.lesson!.class_name">{{ group.lesson!.class_name }}</div>
                  <div class="lesson-meta" v-if="view !== 'teacher' && group.lesson!.teacher_name">{{ group.lesson!.teacher_name }}</div>
                  <div class="lesson-meta" v-if="view !== 'room' && group.lesson!.room_name">{{ group.lesson!.room_name }}</div>
                </div>
              </template>

              <!-- Drop target hint while dragging: green checkmark or red X -->
              <div
                v-if="dragging && dragOverCell?.day === dayIdx && dragOverCell?.slot === slot"
                class="drop-hint"
              >
                <template v-if="canDrop(dayIdx, slot)">
                  <q-icon name="check_circle" size="sm" color="positive" />
                </template>
                <template v-else>
                  <q-icon name="cancel" size="sm" color="negative" />
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Conflict dialog -->
    <q-dialog v-model="showConflictDialog" persistent>
      <q-card style="min-width: 400px; max-width: 560px">
        <q-card-section class="row items-center q-pb-none">
          <q-icon name="warning" color="warning" size="md" class="q-mr-sm" />
          <div class="text-h6">Incompatibilidades Detetadas</div>
        </q-card-section>

        <q-card-section>
          <p class="text-body2 q-mb-sm">
            A aula que está a mover vai entrar em conflito com aulas já existentes:
          </p>
          <q-list dense bordered separator class="rounded-borders">
            <q-item v-for="(c, i) in conflictDetails" :key="i">
              <q-item-section avatar>
                <q-icon
                  :name="c.type === 'class' ? 'groups' : 'person'"
                  :color="c.type === 'class' ? 'blue-7' : 'deep-orange-7'"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">
                  {{ c.type === 'class' ? 'Conflito de Turma' : 'Conflito de Professor' }}
                </q-item-label>
                <q-item-label caption v-if="c.type === 'class'">
                  A turma <strong>{{ c.class_name }}</strong> já tem
                  <em>{{ c.subject_name }}</em> neste tempo
                </q-item-label>
                <q-item-label caption v-else>
                  O professor <strong>{{ c.teacher_name }}</strong> já tem aula
                  ({{ c.class_name }}: <em>{{ c.subject_name }}</em>) neste tempo
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <q-banner :class="$q.dark.isActive ? 'bg-orange-9' : 'bg-orange-1'" class="q-mt-md" rounded dense>
            <template #avatar><q-icon name="info" color="orange" /></template>
            Ao forçar a mudança, o horário ficará com um conflito visível. Pode corrigir
            movendo as outras aulas para outros tempos.
          </q-banner>
        </q-card-section>

        <q-card-actions align="right" class="q-px-md q-pb-md q-gutter-sm">
          <q-btn flat label="Cancelar" @click="cancelConflict" />
          <q-btn
            color="warning"
            icon="warning"
            label="Mover mesmo assim"
            @click="forceMove"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import type { ScheduledLesson } from 'stores/timetables'

interface SlotInfo {
  slot_number: number
  start_time?: string
  end_time?: string
}

interface ConflictInfo {
  type: 'class' | 'teacher'
  lesson_id: number
  subject_name: string
  class_name: string
  teacher_name?: string
}

const props = defineProps<{
  lessons: ScheduledLesson[]
  slots: SlotInfo[]
  view: 'class' | 'teacher' | 'room'
  timetableId?: number
}>()

const emit = defineEmits<{
  (e: 'lesson-moved'): void
}>()

const $q = useQuasar()

const DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

const dragging = ref<ScheduledLesson | null>(null)
const dragOverCell = ref<{ day: number; slot: number } | null>(null)
const showConflictDialog = ref(false)
const conflictDetails = ref<ConflictInfo[]>([])
const pendingLessonId = ref<number | null>(null)
const pendingMove = ref<{ day: number; slot: number } | null>(null)

const uniqueSlots = computed(() => {
  const nums = props.slots.map((s) => s.slot_number)
  return [...new Set(nums)].sort((a, b) => a - b)
})

function slotLabel(slotNum: number) {
  const slot = props.slots.find((s) => s.slot_number === slotNum)
  if (slot?.start_time) return `${slot.start_time}\n${slot.end_time ?? ''}`
  return `T${slotNum}`
}

function cellLessons(day: number, slot: number): ScheduledLesson[] {
  return props.lessons.filter((l) => l.day_of_week === day && l.slot_number === slot)
}

interface LessonGroup {
  key: string
  type: 'single' | 'paired'
  lesson?: ScheduledLesson
  s1?: ScheduledLesson
  s2?: ScheduledLesson
}

function cellGroups(day: number, slot: number): LessonGroup[] {
  const lessons = cellLessons(day, slot)
  const groups: LessonGroup[] = []
  const used = new Set<number>()
  for (const lesson of lessons) {
    if (used.has(lesson.id)) continue
    if (lesson.is_semestral && lesson.paired_entry_id) {
      const partner = lessons.find(
        (l) => l.curriculum_entry_id === lesson.paired_entry_id && !used.has(l.id)
      )
      if (partner) {
        used.add(lesson.id)
        used.add(partner.id)
        const s1 = lesson.semester === 1 ? lesson : partner
        const s2 = lesson.semester === 2 ? lesson : partner
        groups.push({ key: `pair-${lesson.id}-${partner.id}`, type: 'paired', s1, s2 })
        continue
      }
    }
    used.add(lesson.id)
    groups.push({ key: `single-${lesson.id}`, type: 'single', lesson })
  }
  return groups
}

function cardStyle(lesson: ScheduledLesson) {
  const color = lesson.subject_color ?? '#3498db'
  return {
    background: color + '22',
    borderLeft: `4px solid ${color}`,
    borderRadius: '4px',
    padding: '4px 6px',
    minHeight: '44px',
  }
}

function halfStyle(lesson: ScheduledLesson) {
  const color = lesson.subject_color ?? '#3498db'
  return {
    borderLeft: `4px solid ${color}`,
    background: color + '18',
    padding: '3px 5px',
  }
}

function canDrop(day: number, slot: number): boolean {
  if (!dragging.value) return false
  return !props.lessons.some(
    (l) => l.day_of_week === day && l.slot_number === slot && l.id !== dragging.value!.id
  )
}

function getCellClass(day: number, slot: number): string {
  if (!dragging.value) return ''
  const isSource = dragging.value.day_of_week === day && dragging.value.slot_number === slot
  const isHover = dragOverCell.value?.day === day && dragOverCell.value?.slot === slot
  if (isSource) return 'cell--source'
  if (isHover) return canDrop(day, slot) ? 'cell--over-ok' : 'cell--over-conflict'
  return ''
}

function onDragStart(event: DragEvent, lesson: ScheduledLesson) {
  if (!props.timetableId) return
  dragging.value = lesson
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(lesson.id))
  }
}

function onDragEnd() {
  dragging.value = null
  dragOverCell.value = null
}

function onDragOver(event: DragEvent, day: number, slot: number) {
  if (!dragging.value) return
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
  dragOverCell.value = { day, slot }
}

async function onDrop(day: number, slot: number) {
  const lesson = dragging.value
  dragging.value = null
  dragOverCell.value = null
  if (!lesson || !props.timetableId) return
  if (lesson.day_of_week === day && lesson.slot_number === slot) return
  await attemptMove(lesson.id, day, slot, false)
}

async function attemptMove(lessonId: number, day: number, slot: number, force: boolean) {
  try {
    await api.patch(`/timetables/${props.timetableId}/lessons/${lessonId}`, {
      day_of_week: day,
      slot_number: slot,
      force,
    })
    $q.notify({ color: 'positive', message: 'Aula movida', icon: 'check_circle' })
    emit('lesson-moved')
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: { conflicts?: ConflictInfo[] } } } }
    if (err.response?.status === 409) {
      conflictDetails.value = err.response.data?.detail?.conflicts ?? []
      pendingLessonId.value = lessonId
      pendingMove.value = { day, slot }
      showConflictDialog.value = true
    } else {
      $q.notify({ color: 'negative', message: 'Erro ao mover aula', icon: 'error' })
    }
  }
}

function cancelConflict() {
  showConflictDialog.value = false
  conflictDetails.value = []
  pendingLessonId.value = null
  pendingMove.value = null
}

async function forceMove() {
  if (pendingLessonId.value === null || !pendingMove.value) return
  const lid = pendingLessonId.value
  const mv = pendingMove.value
  cancelConflict()
  await attemptMove(lid, mv.day, mv.slot, true)
}
</script>

<style scoped>
.tt-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
  user-select: none;
}

.tt-th {
  padding: 6px 10px;
  border: 1px solid #ddd;
  background: #2c3e50;
  color: white;
  min-width: 120px;
}
.tt-th--time { min-width: 80px; }

.tt-td {
  border: 1px solid #ddd;
  vertical-align: top;
}
.tt-td--time {
  padding: 4px 8px;
  text-align: center;
  background: #ecf0f1;
  color: #2c3e50;
  font-weight: bold;
  font-size: 12px;
  white-space: pre-line;
}
.tt-td--cell {
  padding: 3px;
  min-width: 120px;
  min-height: 50px;
  transition: background 0.12s, outline 0.12s;
  position: relative;
}

/* Dark mode overrides */
.body--dark .tt-th { border-color: #444; }
.body--dark .tt-td { border-color: #444; }
.body--dark .tt-td--time {
  background: #1e2a38;
  color: #90caf9;
}
.body--dark .cell--source { background: #2a2a2a !important; }
.body--dark .cell--over-ok {
  background: #1b3a2a !important;
  outline-color: #66bb6a;
}
.body--dark .cell--over-conflict {
  background: #3a1515 !important;
  outline-color: #ef5350;
}

/* Lesson card */
.lesson-card {
  position: relative;
  margin-bottom: 2px;
  cursor: grab;
}
.lesson-card:active { cursor: grabbing; }
.lesson-card--dragging { opacity: 0.35; }
.lesson-drag-icon {
  position: absolute;
  top: 2px;
  right: 2px;
  opacity: 0.45;
}
.lesson-subject { font-weight: bold; }
.lesson-meta { font-size: 11px; opacity: 0.8; }

/* Paired semestral block */
.lesson-card--paired {
  cursor: default;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #ccc;
}
.body--dark .lesson-card--paired { border-color: #555; }
.paired-half {
  padding: 3px 5px;
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.paired-divider {
  height: 1px;
  background: rgba(0,0,0,0.15);
}
.body--dark .paired-divider { background: rgba(255,255,255,0.15); }
.paired-sem-tag {
  font-size: 10px;
  font-weight: 700;
  opacity: 0.7;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Drop hint */
.drop-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  opacity: 0.85;
  pointer-events: none;
}

/* Cell states during drag */
.drag-active .tt-td--cell { cursor: copy; }

.cell--source {
  background: #f5f5f5 !important;
}
.cell--over-ok {
  background: #e8f5e9 !important;
  outline: 2px solid #43a047;
  outline-offset: -2px;
}
.cell--over-conflict {
  background: #ffebee !important;
  outline: 2px solid #e53935;
  outline-offset: -2px;
}
</style>
