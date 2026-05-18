import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'boot/axios'

export interface Cluster {
  id: number
  name: string
  description?: string
  created_at?: string
}

export const useClustersStore = defineStore('clusters', () => {
  const clusters = ref<Cluster[]>([])
  const loading = ref(false)
  const current = ref<Cluster | null>(null)

  async function fetchAll() {
    loading.value = true
    try {
      const { data } = await api.get<Cluster[]>('/clusters')
      clusters.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: number) {
    const { data } = await api.get<Cluster>(`/clusters/${id}`)
    current.value = data
    return data
  }

  async function create(payload: Omit<Cluster, 'id' | 'created_at'>) {
    const { data } = await api.post<Cluster>('/clusters', payload)
    clusters.value.push(data)
    return data
  }

  async function update(id: number, payload: Partial<Cluster>) {
    const { data } = await api.put<Cluster>(`/clusters/${id}`, payload)
    const idx = clusters.value.findIndex((c) => c.id === id)
    if (idx !== -1) clusters.value[idx] = data
    return data
  }

  async function remove(id: number) {
    await api.delete(`/clusters/${id}`)
    clusters.value = clusters.value.filter((c) => c.id !== id)
  }

  return { clusters, loading, current, fetchAll, fetchOne, create, update, remove }
})
