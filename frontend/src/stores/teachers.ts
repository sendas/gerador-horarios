import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'boot/axios'

export interface Teacher {
  id: number
  cluster_id: number
  name: string
  email?: string
  max_daily_lessons: number
  preferred_free_day?: number
  min_start_slot?: number | null
  max_end_slot?: number | null
  preferred_shift?: string | null
  max_consecutive_lessons?: number | null
  teaching_component?: number | null
  subject_names?: string[]
  school_ids?: number[]
}

export interface TeacherSchoolAssignment {
  id: number
  teacher_id: number
  school_id: number
  academic_year_id: number
  travel_time_minutes: number
}

export interface TeacherAvailability {
  id: number
  teacher_id: number
  academic_year_id: number
  day_of_week: number
  slot_number: number
  is_available: boolean
}

export const useTeachersStore = defineStore('teachers', () => {
  const teachers = ref<Teacher[]>([])
  const loading = ref(false)

  async function fetchAll(cluster_id?: number) {
    loading.value = true
    try {
      const params = cluster_id ? { cluster_id } : {}
      const { data } = await api.get<Teacher[]>('/teachers', { params })
      teachers.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Omit<Teacher, 'id'>) {
    const { data } = await api.post<Teacher>('/teachers', payload)
    teachers.value.push(data)
    return data
  }

  async function update(id: number, payload: Partial<Teacher>) {
    const { data } = await api.put<Teacher>(`/teachers/${id}`, payload)
    const idx = teachers.value.findIndex((t) => t.id === id)
    if (idx !== -1) teachers.value[idx] = data
    return data
  }

  async function remove(id: number) {
    await api.delete(`/teachers/${id}`)
    teachers.value = teachers.value.filter((t) => t.id !== id)
  }

  async function fetchSchoolAssignments(teacherId: number) {
    const { data } = await api.get<TeacherSchoolAssignment[]>(`/teachers/${teacherId}/school-assignments`)
    return data
  }

  async function addSchoolAssignment(teacherId: number, payload: Omit<TeacherSchoolAssignment, 'id' | 'teacher_id'>) {
    const { data } = await api.post<TeacherSchoolAssignment>(`/teachers/${teacherId}/school-assignments`, payload)
    return data
  }

  async function removeSchoolAssignment(assignmentId: number) {
    await api.delete(`/teachers/school-assignments/${assignmentId}`)
  }

  async function fetchSubjects(teacherId: number) {
    const { data } = await api.get(`/teachers/${teacherId}/subjects`)
    return data
  }

  async function addSubject(teacherId: number, subjectId: number) {
    const { data } = await api.post(`/teachers/${teacherId}/subjects/${subjectId}`)
    return data
  }

  async function removeSubject(teacherId: number, subjectId: number) {
    await api.delete(`/teachers/${teacherId}/subjects/${subjectId}`)
  }

  async function fetchAvailability(teacherId: number, academicYearId?: number) {
    const params = academicYearId ? { academic_year_id: academicYearId } : {}
    const { data } = await api.get<TeacherAvailability[]>(`/teachers/${teacherId}/availability`, { params })
    return data
  }

  async function setAvailabilityBulk(teacherId: number, academicYearId: number, availabilities: Omit<TeacherAvailability, 'id'>[]) {
    const { data } = await api.post(`/teachers/${teacherId}/availability/bulk`, {
      academic_year_id: academicYearId,
      availabilities,
    })
    return data
  }

  return {
    teachers, loading, fetchAll, create, update, remove,
    fetchSchoolAssignments, addSchoolAssignment, removeSchoolAssignment,
    fetchSubjects, addSubject, removeSubject,
    fetchAvailability, setAvailabilityBulk,
  }
})
