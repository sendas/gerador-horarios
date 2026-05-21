import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'boot/axios'

export interface Timetable {
  id: number
  academic_year_id: number
  name: string
  status: string
  solver_status?: string
  generation_log?: string | null
  created_at?: string
  updated_at?: string
}

export interface ScheduledLesson {
  id: number
  timetable_id: number
  day_of_week: number
  slot_number: number
  curriculum_entry_id: number
  teacher_id?: number
  room_id?: number
  semester?: number
  is_semestral?: boolean
  paired_entry_id?: number
  subject_name?: string
  subject_color?: string
  class_name?: string
  teacher_name?: string
  room_name?: string
  paired_subject_name?: string
  paired_subject_color?: string
}

export interface TimetableDetail extends Timetable {
  lessons: ScheduledLesson[]
}

export const useTimetablesStore = defineStore('timetables', () => {
  const timetables = ref<Timetable[]>([])
  const current = ref<TimetableDetail | null>(null)
  const loading = ref(false)
  const generating = ref(false)

  async function fetchAll(academic_year_id?: number) {
    loading.value = true
    try {
      const params = academic_year_id ? { academic_year_id } : {}
      const { data } = await api.get<Timetable[]>('/timetables', { params })
      timetables.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    loading.value = true
    try {
      const { data } = await api.get<TimetableDetail>(`/timetables/${id}`)
      current.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Omit<Timetable, 'id' | 'status' | 'created_at' | 'updated_at'>) {
    const { data } = await api.post<Timetable>('/timetables', payload)
    timetables.value.push(data)
    return data
  }

  async function generate(id: number, options?: Record<string, unknown>) {
    generating.value = true
    try {
      await api.post(`/timetables/${id}/generate`, options ?? {})
      const idx = timetables.value.findIndex((t) => t.id === id)
      if (idx !== -1) timetables.value[idx].status = 'generating'
    } finally {
      generating.value = false
    }
  }

  async function remove(id: number) {
    await api.delete(`/timetables/${id}`)
    timetables.value = timetables.value.filter((t) => t.id !== id)
  }

  async function fetchByTeacher(timetableId: number, teacherId: number) {
    const { data } = await api.get<ScheduledLesson[]>(`/timetables/${timetableId}/by-teacher/${teacherId}`)
    return data
  }

  async function fetchByClass(timetableId: number, classId: number) {
    const { data } = await api.get<ScheduledLesson[]>(`/timetables/${timetableId}/by-class/${classId}`)
    return data
  }

  async function fetchByRoom(timetableId: number, roomId: number) {
    const { data } = await api.get<ScheduledLesson[]>(`/timetables/${timetableId}/by-room/${roomId}`)
    return data
  }

  async function cancelGeneration(id: number) {
    const { data } = await api.put<Timetable>(`/timetables/${id}`, {
      status: 'error',
      solver_status: 'Geração cancelada manualmente.',
    })
    const idx = timetables.value.findIndex((t) => t.id === id)
    if (idx !== -1) timetables.value[idx] = { ...timetables.value[idx], ...data }
  }

  return {
    timetables, current, loading, generating,
    fetchAll, fetchDetail, create, generate, remove, cancelGeneration,
    fetchByTeacher, fetchByClass, fetchByRoom,
  }
})
