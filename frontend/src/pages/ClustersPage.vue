<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Agrupamentos</div>
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn color="primary" icon="add" label="Novo" @click="openCreate" class="q-ml-sm" />
    </div>

    <q-table
      :rows="clustersStore.clusters"
      :columns="columns"
      row-key="id"
      :loading="clustersStore.loading"
      :filter="search"
      sort-by="name"
    >
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openEdit(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">{{ editing ? 'Editar' : 'Novo' }} Agrupamento</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="save">
            <q-input v-model="form.name" label="Nome *" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.description" label="Descrição" type="textarea" rows="2" />
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
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useClustersStore } from 'stores/clusters'

const $q = useQuasar()
const clustersStore = useClustersStore()

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'description', label: 'Descrição', field: 'description', align: 'left' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const search = ref('')
const dialog = ref(false)
const editing = ref<null | { id: number }>(null)
const form = ref({ name: '', description: '' })

onMounted(() => clustersStore.fetchAll())

function openCreate() {
  editing.value = null
  form.value = { name: '', description: '' }
  dialog.value = true
}

function openEdit(row: { id: number; name: string; description?: string }) {
  editing.value = row
  form.value = { name: row.name, description: row.description || '' }
  dialog.value = true
}

async function save() {
  try {
    if (editing.value) {
      await clustersStore.update(editing.value.id, form.value)
      $q.notify({ type: 'positive', message: 'Agrupamento atualizado' })
    } else {
      await clustersStore.create(form.value)
      $q.notify({ type: 'positive', message: 'Agrupamento criado' })
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
    await clustersStore.remove(row.id)
    $q.notify({ type: 'positive', message: 'Eliminado' })
  })
}
</script>
