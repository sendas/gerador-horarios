import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'boot/axios'

export interface School {
  id: number
  cluster_id: number
  name: string
  code: string
  address?: string
  created_at?: string
}

export const useSchoolsStore = defineStore('schools', () => {
  const schools = ref<School[]>([])
  const loading = ref(false)

  async function fetchAll(cluster_id?: number) {
    loading.value = true
    try {
      const params = cluster_id ? { cluster_id } : {}
      const { data } = await api.get<School[]>('/schools', { params })
      schools.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Omit<School, 'id' | 'created_at'>) {
    const { data } = await api.post<School>('/schools', payload)
    schools.value.push(data)
    return data
  }

  async function update(id: number, payload: Partial<School>) {
    const { data } = await api.put<School>(`/schools/${id}`, payload)
    const idx = schools.value.findIndex((s) => s.id === id)
    if (idx !== -1) schools.value[idx] = data
    return data
  }

  async function remove(id: number) {
    await api.delete(`/schools/${id}`)
    schools.value = schools.value.filter((s) => s.id !== id)
  }

  return { schools, loading, fetchAll, create, update, remove }
})
