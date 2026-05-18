import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'boot/axios'

export interface AcademicYear {
  id: number
  cluster_id: number
  name: string
  start_date: string
  end_date: string
  is_active: boolean
  created_at?: string
}

export const useAcademicYearsStore = defineStore('academicYears', () => {
  const years = ref<AcademicYear[]>([])
  const loading = ref(false)

  async function fetchAll(cluster_id?: number) {
    loading.value = true
    try {
      const params = cluster_id ? { cluster_id } : {}
      const { data } = await api.get<AcademicYear[]>('/academic-years', { params })
      years.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Omit<AcademicYear, 'id' | 'created_at'>) {
    const { data } = await api.post<AcademicYear>('/academic-years', payload)
    years.value.push(data)
    return data
  }

  async function update(id: number, payload: Partial<AcademicYear>) {
    const { data } = await api.put<AcademicYear>(`/academic-years/${id}`, payload)
    const idx = years.value.findIndex((y) => y.id === id)
    if (idx !== -1) years.value[idx] = data
    return data
  }

  async function activate(id: number) {
    const { data } = await api.patch<AcademicYear>(`/academic-years/${id}/activate`)
    years.value = years.value.map((y) => ({ ...y, is_active: y.id === id }))
    return data
  }

  async function remove(id: number) {
    await api.delete(`/academic-years/${id}`)
    years.value = years.value.filter((y) => y.id !== id)
  }

  return { years, loading, fetchAll, create, update, activate, remove }
})
