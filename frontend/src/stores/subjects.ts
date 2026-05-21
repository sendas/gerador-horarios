import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'boot/axios'

export interface Subject {
  id: number
  cluster_id: number
  name: string
  code?: string
  color: string
  weekly_structure: string  // '1' | '1+1' | '2' | '2+1' | '1+1+1'
  regime: string            // 'annual' | 'semestral'
  default_semester?: number | null
  paired_subject_id?: number | null
  paired_subject_name?: string | null
  is_physical_education: boolean
  can_exempt_articulado: boolean
}

export const useSubjectsStore = defineStore('subjects', () => {
  const subjects = ref<Subject[]>([])
  const loading = ref(false)

  async function fetchAll(cluster_id?: number) {
    loading.value = true
    try {
      const params = cluster_id ? { cluster_id } : {}
      const { data } = await api.get<Subject[]>('/subjects', { params })
      subjects.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Omit<Subject, 'id'>) {
    const { data } = await api.post<Subject>('/subjects', payload)
    subjects.value.push(data)
    return data
  }

  async function update(id: number, payload: Partial<Subject>) {
    const { data } = await api.put<Subject>(`/subjects/${id}`, payload)
    const idx = subjects.value.findIndex((s) => s.id === id)
    if (idx !== -1) subjects.value[idx] = data
    return data
  }

  async function remove(id: number) {
    await api.delete(`/subjects/${id}`)
    subjects.value = subjects.value.filter((s) => s.id !== id)
  }

  return { subjects, loading, fetchAll, create, update, remove }
})
