<template>
  <div class="timetable-grid">
    <table style="border-collapse:collapse;width:100%;font-size:13px">
      <thead>
        <tr>
          <th style="padding:6px 10px;border:1px solid #ddd;background:#2c3e50;color:white;min-width:80px">Hora</th>
          <th v-for="day in DAYS" :key="day" style="padding:6px 10px;border:1px solid #ddd;background:#2c3e50;color:white;min-width:120px">{{ day }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="slot in uniqueSlots" :key="slot">
          <td style="padding:4px 8px;border:1px solid #ddd;text-align:center;background:#ecf0f1;font-weight:bold;font-size:12px">
            {{ slotLabel(slot) }}
          </td>
          <td v-for="(day, dayIdx) in DAYS" :key="dayIdx" style="padding:3px;border:1px solid #ddd;vertical-align:top">
            <div v-if="cellLesson(dayIdx, slot)" class="lesson-cell" :style="cellStyle(cellLesson(dayIdx, slot))">
              <div style="font-weight:bold">{{ cellLesson(dayIdx, slot)?.subject_name }}</div>
              <div style="font-size:11px;opacity:0.8" v-if="view !== 'class'">{{ cellLesson(dayIdx, slot)?.class_name }}</div>
              <div style="font-size:11px;opacity:0.8" v-if="view !== 'teacher'">{{ cellLesson(dayIdx, slot)?.teacher_name }}</div>
              <div style="font-size:11px;opacity:0.7" v-if="view !== 'room' && cellLesson(dayIdx, slot)?.room_name">{{ cellLesson(dayIdx, slot)?.room_name }}</div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ScheduledLesson } from 'stores/timetables'

interface SlotInfo {
  slot_number: number
  start_time?: string
  end_time?: string
}

const props = defineProps<{
  lessons: ScheduledLesson[]
  slots: SlotInfo[]
  view: 'class' | 'teacher' | 'room'
}>()

const DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

const uniqueSlots = computed(() => {
  const nums = props.slots.map((s) => s.slot_number)
  return [...new Set(nums)].sort((a, b) => a - b)
})

function slotLabel(slotNum: number) {
  const slot = props.slots.find((s) => s.slot_number === slotNum)
  if (slot?.start_time) return `${slot.start_time}\n${slot.end_time ?? ''}`
  return `T${slotNum}`
}

function cellLesson(day: number, slot: number) {
  return props.lessons.find((l) => l.day_of_week === day && l.slot_number === slot) ?? null
}

function cellStyle(lesson: ScheduledLesson | null) {
  if (!lesson) return {}
  const color = lesson.subject_color ?? '#3498db'
  return {
    background: color + '22',
    borderLeft: `4px solid ${color}`,
    borderRadius: '3px',
    padding: '4px 6px',
    minHeight: '40px',
  }
}
</script>
