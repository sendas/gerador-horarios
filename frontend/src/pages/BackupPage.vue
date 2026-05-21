<template>
  <q-page padding>
    <div class="text-h5 q-mb-lg">
      <q-icon name="cloud_sync" color="blue-grey-7" class="q-mr-sm" />
      Cópias de Segurança
    </div>

    <!-- Status card -->
    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-sm-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-grey-7 q-mb-sm">Último backup</div>
            <div class="text-h6" v-if="config?.last_backup_at">
              {{ formatDate(config.last_backup_at) }}
            </div>
            <div class="text-grey-5" v-else>Nunca realizado</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-grey-7 q-mb-sm">OneDrive</div>
            <q-chip
              :icon="config?.onedrive_connected ? 'cloud_done' : 'cloud_off'"
              :color="config?.onedrive_connected ? 'positive' : 'grey-4'"
              :text-color="config?.onedrive_connected ? 'white' : 'grey-7'"
            >
              {{ config?.onedrive_connected ? 'Ligado' : 'Não ligado' }}
            </q-chip>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Backup actions -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">
          <q-icon name="backup" color="blue-7" class="q-mr-sm" />Fazer Backup
        </div>
        <div class="row q-gutter-sm">
          <q-btn
            color="primary" icon="download" label="Descarregar Backup"
            :loading="downloading" @click="downloadBackup"
          />
          <q-btn
            color="teal" icon="cloud_upload" label="Enviar para OneDrive"
            :disable="!config?.onedrive_connected" :loading="backing"
            @click="backupNow"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Frequency config -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">
          <q-icon name="schedule" color="purple-6" class="q-mr-sm" />Frequência Automática
        </div>
        <q-toggle v-model="form.enabled" label="Backups automáticos ativos" color="primary" class="q-mb-md" />
        <div v-if="form.enabled">
          <q-btn-toggle
            v-model="form.frequency"
            :options="freqOptions"
            rounded unelevated
            color="white" text-color="primary"
            toggle-color="primary" toggle-text-color="white"
            class="bordered q-mb-sm"
          />
          <div class="text-caption text-grey-6">
            O backup automático é enviado para OneDrive (se ligado) ou registado no histórico.
          </div>
        </div>
        <div class="row justify-end q-mt-md">
          <q-btn color="primary" icon="save" label="Guardar" :loading="saving" @click="saveConfig" />
        </div>
      </q-card-section>
    </q-card>

    <!-- OneDrive connection -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-sm">
          <q-icon name="cloud" color="blue-8" class="q-mr-sm" />Ligar ao OneDrive
        </div>
        <q-banner v-if="!config?.onedrive_connected" :class="$q.dark.isActive ? 'bg-blue-9' : 'bg-blue-1'" class="q-mb-md" rounded dense>
          <template #avatar><q-icon name="info" color="blue" /></template>
          Para ligar ao OneDrive é necessário um <strong>Client ID</strong> de uma aplicação registada no
          <a href="https://portal.azure.com" target="_blank" class="text-primary">portal.azure.com</a>.
          <q-expansion-item label="Como registar a aplicação" dense class="q-mt-xs">
            <ol class="q-mt-xs text-body2">
              <li>Acede a <strong>portal.azure.com → Microsoft Entra ID → Registos de aplicações</strong></li>
              <li>Clica em <strong>"Novo registo"</strong></li>
              <li>Nome: "Gerador Horários Backup". Tipo: <em>Contas pessoais Microsoft</em></li>
              <li>Em <strong>"Autenticação"</strong>, ativa <em>"Permitir fluxos de cliente público"</em></li>
              <li>Em <strong>"Permissões de API"</strong>, adiciona: <code>Files.ReadWrite</code> e <code>offline_access</code></li>
              <li>Copia o <strong>ID da Aplicação (cliente)</strong> e cola abaixo</li>
            </ol>
          </q-expansion-item>
        </q-banner>

        <div v-if="!config?.onedrive_connected">
          <q-input v-model="clientId" label="Client ID da aplicação Azure" outlined dense class="q-mb-sm" />
          <q-input v-model="form.folder_path" label="Pasta no OneDrive" outlined dense hint="Ex: GeradorHorarios/Backups" class="q-mb-md" />
          <q-btn color="blue-8" icon="login" label="Iniciar autorização" :loading="authLoading" :disable="!clientId" @click="startAuth" />
        </div>

        <!-- Device code step -->
        <div v-if="deviceCode" class="q-mt-md">
          <q-banner class="bg-amber-1 rounded-borders" dense>
            <template #avatar><q-icon name="smartphone" color="amber-9" /></template>
            <div>
              1. Abre <a :href="verificationUri" target="_blank" class="text-primary">{{ verificationUri }}</a><br>
              2. Introduz o código: <strong class="text-h6 text-primary">{{ userCode }}</strong>
            </div>
          </q-banner>
          <div class="row items-center q-gutter-sm q-mt-sm">
            <q-btn color="positive" icon="check_circle" label="Verificar autorização" :loading="polling" @click="pollAuth" />
            <q-btn flat label="Cancelar" @click="cancelAuth" />
          </div>
        </div>

        <div v-if="config?.onedrive_connected" class="row items-center q-gutter-sm">
          <q-icon name="check_circle" color="positive" size="md" />
          <span class="text-positive text-weight-medium">OneDrive ligado com sucesso</span>
          <q-space />
          <q-btn flat color="negative" icon="link_off" label="Desligar" @click="disconnect" />
        </div>
      </q-card-section>
    </q-card>

    <!-- History -->
    <q-card flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">
          <q-icon name="history" color="grey-7" class="q-mr-sm" />Histórico
        </div>
        <div class="row items-center q-mb-sm">
          <q-space />
          <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </div>
        <q-table
          :rows="history"
          :columns="histCols"
          row-key="id"
          dense flat
          :rows-per-page-options="[10]"
          :filter="search"
          sort-by="created_at"
          :descending="true"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="props.row.status === 'success' ? 'positive' : 'negative'" :label="props.row.status" />
            </q-td>
          </template>
          <template #body-cell-destination="props">
            <q-td :props="props">
              <q-icon :name="props.row.destination === 'onedrive' ? 'cloud' : 'download'" size="xs" class="q-mr-xs" />
              {{ props.row.destination }}
            </q-td>
          </template>
          <template #body-cell-size_bytes="props">
            <q-td :props="props">
              {{ props.row.size_bytes ? (props.row.size_bytes / 1024).toFixed(1) + ' KB' : '—' }}
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

const $q = useQuasar()

interface BackupConfigResponse {
  enabled: boolean
  frequency: string
  onedrive_client_id: string | null
  onedrive_connected: boolean
  folder_path: string
  last_backup_at: string | null
  next_backup_at: string | null
}

const search = ref('')
const config = ref<BackupConfigResponse | null>(null)
const history = ref<Record<string, unknown>[]>([])
const downloading = ref(false)
const backing = ref(false)
const saving = ref(false)
const authLoading = ref(false)
const polling = ref(false)

const clientId = ref('')
const deviceCode = ref('')
const userCode = ref('')
const verificationUri = ref('')

const form = ref({ enabled: false, frequency: 'weekly', folder_path: 'GeradorHorarios/Backups' })

const freqOptions = [
  { label: 'Manual', value: 'manual' },
  { label: 'Diário', value: 'daily' },
  { label: 'Semanal', value: 'weekly' },
  { label: 'Mensal', value: 'monthly' },
]

const histCols = [
  { name: 'created_at', label: 'Data/Hora', field: 'created_at', align: 'left' as const },
  { name: 'status', label: 'Estado', field: 'status', align: 'center' as const },
  { name: 'destination', label: 'Destino', field: 'destination', align: 'center' as const },
  { name: 'size_bytes', label: 'Tamanho', field: 'size_bytes', align: 'right' as const },
  { name: 'filename', label: 'Ficheiro', field: 'filename', align: 'left' as const },
]

function formatDate(d: string) {
  return new Date(d).toLocaleString('pt-PT')
}

async function load() {
  const [cfgRes, histRes] = await Promise.all([api.get('/backup/config'), api.get('/backup/history')])
  config.value = cfgRes.data
  history.value = histRes.data
  form.value.enabled = config.value?.enabled ?? false
  form.value.frequency = config.value?.frequency ?? 'weekly'
  form.value.folder_path = config.value?.folder_path ?? 'GeradorHorarios/Backups'
  clientId.value = config.value?.onedrive_client_id ?? ''
}

async function downloadBackup() {
  downloading.value = true
  try {
    const resp = await api.get('/backup/download', { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `backup_${new Date().toISOString().slice(0,10)}.json.gz`
    a.click()
    URL.revokeObjectURL(url)
    await load()
  } catch { $q.notify({ type: 'negative', message: 'Erro ao descarregar backup' }) }
  finally { downloading.value = false }
}

async function backupNow() {
  backing.value = true
  try {
    await api.post('/backup/now')
    $q.notify({ type: 'positive', message: 'Backup iniciado em segundo plano' })
    setTimeout(load, 3000)
  } catch { $q.notify({ type: 'negative', message: 'Erro ao iniciar backup' }) }
  finally { backing.value = false }
}

async function saveConfig() {
  saving.value = true
  try {
    await api.put('/backup/config', {
      enabled: form.value.enabled,
      frequency: form.value.frequency,
      folder_path: form.value.folder_path,
    })
    $q.notify({ type: 'positive', message: 'Configuração guardada' })
    await load()
  } catch { $q.notify({ type: 'negative', message: 'Erro ao guardar' }) }
  finally { saving.value = false }
}

async function startAuth() {
  authLoading.value = true
  try {
    const { data } = await api.post('/backup/onedrive/start-auth', { client_id: clientId.value })
    deviceCode.value = data.device_code
    userCode.value = data.user_code
    verificationUri.value = data.verification_uri
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    $q.notify({ type: 'negative', message: err.response?.data?.detail ?? 'Erro ao iniciar autorização' })
  } finally { authLoading.value = false }
}

async function pollAuth() {
  polling.value = true
  try {
    const { data } = await api.post('/backup/onedrive/poll-auth', {
      client_id: clientId.value,
      device_code: deviceCode.value,
    })
    if (data.status === 'pending') {
      $q.notify({ type: 'info', message: 'Ainda a aguardar autorização — tenta novamente em breve' })
    } else {
      deviceCode.value = ''
      $q.notify({ type: 'positive', message: 'OneDrive ligado com sucesso!' })
      await load()
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    $q.notify({ type: 'negative', message: err.response?.data?.detail ?? 'Erro ao verificar autorização' })
  } finally { polling.value = false }
}

function cancelAuth() {
  deviceCode.value = ''; userCode.value = ''; verificationUri.value = ''
}

async function disconnect() {
  await api.delete('/backup/onedrive/disconnect')
  $q.notify({ type: 'positive', message: 'OneDrive desligado' })
  await load()
}

onMounted(load)
</script>
