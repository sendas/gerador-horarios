<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5">Utilizadores</div>
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn color="primary" icon="add" label="Novo utilizador" @click="openCreate" class="q-ml-sm" />
    </div>

    <q-table
      :rows="users"
      :columns="columns"
      row-key="id"
      :loading="loading"
      flat
      bordered
      :filter="search"
      sort-by="username"
    >
      <template #body-cell-role="props">
        <q-td :props="props">
          <q-badge :color="roleColor(props.value)">{{ props.value }}</q-badge>
        </q-td>
      </template>

      <template #body-cell-is_active="props">
        <q-td :props="props">
          <q-icon :name="props.value ? 'check_circle' : 'cancel'" :color="props.value ? 'positive' : 'negative'" />
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props" class="q-gutter-xs">
          <q-btn flat dense icon="edit" color="primary" @click="openEdit(props.row)">
            <q-tooltip>Editar</q-tooltip>
          </q-btn>
          <q-btn flat dense icon="lock_reset" color="warning" @click="openResetPassword(props.row)">
            <q-tooltip>Redefinir palavra-passe</q-tooltip>
          </q-btn>
          <q-btn
            flat dense icon="delete" color="negative"
            :disable="props.row.id === auth.user?.id"
            @click="confirmDelete(props.row)"
          >
            <q-tooltip>Eliminar</q-tooltip>
          </q-btn>
        </q-td>
      </template>
    </q-table>

    <!-- Create/Edit dialog -->
    <q-dialog v-model="showDialog" persistent>
      <q-card style="min-width: 380px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">{{ editTarget ? 'Editar utilizador' : 'Novo utilizador' }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-gutter-md">
          <q-input
            v-if="!editTarget"
            v-model="form.username"
            label="Nome de utilizador"
            outlined
            :rules="[(v) => !!v || 'Obrigatório']"
          />
          <q-input
            v-model="form.full_name"
            label="Nome completo"
            outlined
          />
          <q-select
            v-model="form.role"
            label="Papel"
            outlined
            :options="roleOptions"
            emit-value
            map-options
          />
          <q-toggle v-if="editTarget" v-model="form.is_active" label="Conta ativa" />
          <q-input
            v-if="!editTarget"
            v-model="form.password"
            label="Palavra-passe inicial"
            outlined
            type="password"
            :rules="[(v) => !!v || 'Obrigatória']"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn color="primary" label="Guardar" :loading="saving" @click="save" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Reset password dialog -->
    <q-dialog v-model="showResetDialog" persistent>
      <q-card style="min-width: 340px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Redefinir palavra-passe</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-input v-model="newPassword" label="Nova palavra-passe" outlined type="password" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn color="warning" label="Redefinir" :loading="saving" @click="resetPassword" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAuthStore } from 'stores/auth'

const $q = useQuasar()
const auth = useAuthStore()

interface UserRow {
  id: number
  username: string
  full_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

const search = ref('')
const users = ref<UserRow[]>([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const showResetDialog = ref(false)
const editTarget = ref<UserRow | null>(null)
const newPassword = ref('')

const form = ref({ username: '', full_name: '', role: 'user', is_active: true, password: '' })

const columns = [
  { name: 'username', label: 'Utilizador', field: 'username', sortable: true, align: 'left' as const },
  { name: 'full_name', label: 'Nome completo', field: 'full_name', sortable: true, align: 'left' as const },
  { name: 'role', label: 'Papel', field: 'role', sortable: true, align: 'left' as const },
  { name: 'is_active', label: 'Ativo', field: 'is_active', align: 'center' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const roleOptions = [
  { label: 'Administrador', value: 'admin' },
  { label: 'Utilizador', value: 'user' },
  { label: 'Visualizador', value: 'viewer' },
]

function roleColor(role: string) {
  return role === 'admin' ? 'red-7' : role === 'viewer' ? 'grey-6' : 'primary'
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/auth/users')
    users.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editTarget.value = null
  form.value = { username: '', full_name: '', role: 'user', is_active: true, password: '' }
  showDialog.value = true
}

function openEdit(row: UserRow) {
  editTarget.value = row
  form.value = { username: row.username, full_name: row.full_name ?? '', role: row.role, is_active: row.is_active, password: '' }
  showDialog.value = true
}

function openResetPassword(row: UserRow) {
  editTarget.value = row
  newPassword.value = ''
  showResetDialog.value = true
}

async function save() {
  saving.value = true
  try {
    if (editTarget.value) {
      await api.put(`/auth/users/${editTarget.value.id}`, {
        full_name: form.value.full_name || null,
        role: form.value.role,
        is_active: form.value.is_active,
      })
    } else {
      await api.post('/auth/users', {
        username: form.value.username,
        password: form.value.password,
        full_name: form.value.full_name || null,
        role: form.value.role,
      })
    }
    showDialog.value = false
    await load()
    $q.notify({ color: 'positive', message: 'Guardado com sucesso' })
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    $q.notify({ color: 'negative', message: err.response?.data?.detail ?? 'Erro ao guardar' })
  } finally {
    saving.value = false
  }
}

async function resetPassword() {
  if (!newPassword.value) return
  saving.value = true
  try {
    await api.put(`/auth/users/${editTarget.value!.id}/reset-password`, { password: newPassword.value })
    showResetDialog.value = false
    $q.notify({ color: 'positive', message: 'Palavra-passe redefinida' })
  } catch {
    $q.notify({ color: 'negative', message: 'Erro ao redefinir palavra-passe' })
  } finally {
    saving.value = false
  }
}

function confirmDelete(row: UserRow) {
  $q.dialog({
    title: 'Eliminar utilizador',
    message: `Confirma a eliminação de "${row.username}"?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    await api.delete(`/auth/users/${row.id}`)
    await load()
    $q.notify({ color: 'positive', message: 'Utilizador eliminado' })
  })
}

onMounted(load)
</script>
