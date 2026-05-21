<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Salas</div>
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn color="primary" icon="add" label="Nova" @click="openCreate" class="q-ml-sm" />
      <q-btn color="secondary" icon="upload" label="Importar" @click="showImport = true" class="q-ml-sm" />
    </div>

    <ImportDialog
      v-model="showImport"
      title="Importar Salas"
      endpoint="/imports/rooms"
      :extra-params="{ school_id: filterSchool }"
      entity-type="rooms"
      @done="loadRooms()"
    />

    <div class="q-mb-md">
      <q-select v-model="filterSchool" :options="schoolOptions" label="Filtrar por escola" emit-value map-options clearable style="max-width:300px" @update:model-value="loadRooms" />
    </div>

    <q-table :rows="rooms" :columns="columns" row-key="id" :loading="loading" :filter="search" sort-by="name">
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openEdit(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 400px">
        <q-card-section><div class="text-h6">{{ editing ? 'Editar' : 'Nova' }} Sala</div></q-card-section>
        <q-card-section>
          <q-form @submit="save">
            <q-select v-model="form.school_id" :options="schoolOptions" label="Escola *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.name" label="Nome *" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model.number="form.capacity" label="Capacidade" type="number" min="1" />
            <q-input v-model="form.room_type" label="Tipo" />
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" :label="editing ? 'Guardar' : 'Criar'" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useSchoolsStore } from 'stores/schools'
import ImportDialog from 'components/ImportDialog.vue'

const $q = useQuasar()
const schoolsStore = useSchoolsStore()

const search = ref('')
const showImport = ref(false)
const rooms = ref<{ id: number; school_id: number; name: string; capacity: number; room_type: string }[]>([])
const loading = ref(false)
const filterSchool = ref<number | null>(null)
const dialog = ref(false)
const editing = ref<null | { id: number }>(null)
const form = ref({ school_id: null as number | null, name: '', capacity: 30, room_type: 'classroom' })

const schoolOptions = computed(() => schoolsStore.schools.map((s) => ({ label: s.name, value: s.id })))

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const },
  { name: 'school', label: 'Escola', field: (r: { school_id: number }) => schoolsStore.schools.find(s => s.id === r.school_id)?.name ?? '—', align: 'left' as const },
  { name: 'capacity', label: 'Capacidade', field: 'capacity', align: 'center' as const },
  { name: 'room_type', label: 'Tipo', field: 'room_type', align: 'left' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

async function loadRooms() {
  loading.value = true
  try {
    const params: Record<string, number> = {}
    if (filterSchool.value) params.school_id = filterSchool.value
    const { data } = await api.get('/rooms', { params })
    rooms.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = { school_id: null, name: '', capacity: 30, room_type: 'classroom' }
  dialog.value = true
}

function openEdit(row: { id: number; school_id: number; name: string; capacity: number; room_type: string }) {
  editing.value = row
  form.value = { school_id: row.school_id, name: row.name, capacity: row.capacity, room_type: row.room_type }
  dialog.value = true
}

async function save() {
  if (!form.value.school_id) return
  try {
    if (editing.value) {
      const { data } = await api.put(`/rooms/${editing.value.id}`, form.value)
      const idx = rooms.value.findIndex((r) => r.id === (editing.value as { id: number }).id)
      if (idx !== -1) rooms.value[idx] = data
      $q.notify({ type: 'positive', message: 'Sala atualizada' })
    } else {
      const { data } = await api.post('/rooms', form.value)
      rooms.value.push(data)
      $q.notify({ type: 'positive', message: 'Sala criada' })
    }
    dialog.value = false
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar' })
  }
}

function confirmDelete(row: { id: number; name: string }) {
  $q.dialog({
    title: 'Confirmar eliminação',
    message: `Eliminar "${row.name}"?`,
    ok: { label: 'Eliminar', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    await api.delete(`/rooms/${row.id}`)
    rooms.value = rooms.value.filter((r) => r.id !== row.id)
    $q.notify({ type: 'positive', message: 'Eliminada' })
  })
}

onMounted(async () => {
  await schoolsStore.fetchAll()
  await loadRooms()
})
</script>
