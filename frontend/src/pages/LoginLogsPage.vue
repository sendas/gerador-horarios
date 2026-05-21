<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm">
      <q-icon name="history" size="sm" color="blue-grey-6" />
      <span class="text-h6">Registo de Acessos</span>
      <q-space />
      <q-input
        v-model="filterUser"
        dense outlined clearable
        placeholder="Filtrar utilizador…"
        style="width: 220px"
        @update:model-value="load"
      />
      <q-btn flat round icon="refresh" @click="load" :loading="loading" />
    </div>

    <q-table
      :rows="logs"
      :columns="columns"
      row-key="id"
      :loading="loading"
      flat bordered
      :rows-per-page-options="[50, 100, 200]"
      rows-per-page-label="Linhas por página"
      :pagination="{ rowsPerPage: 50, sortBy: 'timestamp', descending: true }"
      :filter="filterUser"
      sort-by="timestamp"
      :descending="true"
    >
      <template #body-cell-success="{ row }">
        <q-td>
          <q-chip
            dense
            :color="row.success ? 'positive' : 'negative'"
            text-color="white"
            :label="row.success ? 'Sucesso' : 'Falhou'"
            size="sm"
          />
        </q-td>
      </template>

      <template #body-cell-action="{ row }">
        <q-td>
          <q-chip
            dense size="sm"
            :color="actionColor(row.action)"
            text-color="white"
            :label="actionLabel(row.action)"
          />
        </q-td>
      </template>

      <template #body-cell-timestamp="{ row }">
        <q-td>{{ formatDate(row.timestamp) }}</q-td>
      </template>

      <template #body-cell-user_agent="{ row }">
        <q-td>
          <span class="text-caption text-grey-6 ellipsis" style="max-width: 200px; display: block">
            {{ row.user_agent || '—' }}
          </span>
        </q-td>
      </template>
    </q-table>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from 'boot/axios'
import { date } from 'quasar'

interface LogEntry {
  id: number
  timestamp: string
  username: string
  user_id: number | null
  action: string
  success: boolean
  ip_address: string | null
  user_agent: string | null
}

const logs = ref<LogEntry[]>([])
const loading = ref(false)
const filterUser = ref('')

const columns = [
  { name: 'timestamp', label: 'Data / Hora', field: 'timestamp', sortable: true, align: 'left' as const },
  { name: 'username', label: 'Utilizador', field: 'username', sortable: true, align: 'left' as const },
  { name: 'action', label: 'Ação', field: 'action', sortable: true, align: 'left' as const },
  { name: 'success', label: 'Estado', field: 'success', sortable: true, align: 'left' as const },
  { name: 'ip_address', label: 'IP', field: 'ip_address', align: 'left' as const },
  { name: 'user_agent', label: 'Browser / Cliente', field: 'user_agent', align: 'left' as const },
]

function actionLabel(action: string): string {
  const map: Record<string, string> = {
    login: 'Login',
    login_failed: 'Login falhado',
    demo_login: 'Demo',
  }
  return map[action] ?? action
}

function actionColor(action: string): string {
  if (action === 'login') return 'primary'
  if (action === 'login_failed') return 'negative'
  if (action === 'demo_login') return 'teal'
  return 'grey'
}

function formatDate(ts: string): string {
  return date.formatDate(new Date(ts), 'DD/MM/YYYY HH:mm:ss')
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { limit: 200 }
    if (filterUser.value) params.username = filterUser.value
    const { data } = await api.get('/auth/login-logs', { params })
    logs.value = data
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
