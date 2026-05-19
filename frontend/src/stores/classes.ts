import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'boot/axios'

export interface SchoolClass {
  id: number
  school_id: number
  academic_year_id: number
  name: string
  year_level: number
  num_students: number
  notes?: string | null
}

export interface CurriculumEntry {
  id: number
  class_id: number
  subject_id: number
  hours_per_week: number
  is_split: boolean
  split_count: number
  consecutive_pairs: number
  is_semestral: boolean
  semester: number | null
  paired_entry_id: number | null
}

export const useClassesStore = defineStore('classes', () => {
  const classes = ref<SchoolClass[]>([])
  const loading = ref(false)

  async function fetchAll(params?: { school_id?: number; academic_year_id?: number }) {
    loading.value = true
    try {
      const { data } = await api.get<SchoolClass[]>('/classes', { params })
      classes.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Omit<SchoolClass, 'id'>) {
    const { data } = await api.post<SchoolClass>('/classes', payload)
    classes.value.push(data)
    return data
  }

  async function update(id: number, payload: Partial<SchoolClass>) {
    const { data } = await api.put<SchoolClass>(`/classes/${id}`, payload)
    const idx = classes.value.findIndex((c) => c.id === id)
    if (idx !== -1) classes.value[idx] = data
    return data
  }

  async function remove(id: number) {
    await api.delete(`/classes/${id}`)
    classes.value = classes.value.filter((c) => c.id !== id)
  }

  async function fetchCurriculum(classId: number) {
    const { data } = await api.get<CurriculumEntry[]>(`/classes/${classId}/curriculum`)
    return data
  }

  async function addCurriculumEntry(classId: number, payload: Omit<CurriculumEntry, 'id' | 'class_id'>) {
    const { data } = await api.post<CurriculumEntry>(`/classes/${classId}/curriculum`, payload)
    return data
  }

  async function updateCurriculumEntry(entryId: number, payload: Partial<CurriculumEntry>) {
    const { data } = await api.put<CurriculumEntry>(`/classes/curriculum/${entryId}`, payload)
    return data
  }

  async function removeCurriculumEntry(entryId: number) {
    await api.delete(`/classes/curriculum/${entryId}`)
  }

  return {
    classes, loading, fetchAll, create, update, remove,
    fetchCurriculum, addCurriculumEntry, updateCurriculumEntry, removeCurriculumEntry
  }
})
