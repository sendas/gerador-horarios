<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Escolas</div>
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn color="primary" icon="add" label="Nova" @click="openCreate" class="q-ml-sm" />
    </div>

    <q-table
      :rows="schoolsStore.schools"
      :columns="columns"
      row-key="id"
      :loading="schoolsStore.loading"
      :filter="search"
      sort-by="name"
    >
      <template #body-cell-cluster="props">
        <q-td :props="props">
          {{ clusterName(props.row.cluster_id) }}
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openEdit(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 450px">
        <q-card-section>
          <div class="text-h6">{{ editing ? 'Editar' : 'Nova' }} Escola</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="save">
            <q-select
              v-model="form.cluster_id"
              :options="clusterOptions"
              label="Agrupamento *"
              emit-value map-options
              :rules="[v => !!v || 'Obrigatório']"
            />
            <q-input v-model="form.name" label="Nome *" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.code" label="Código *" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.address" label="Morada" />
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
import { useSchoolsStore } from 'stores/schools'
import { useClustersStore } from 'stores/clusters'

const $q = useQuasar()
const schoolsStore = useSchoolsStore()
const clustersStore = useClustersStore()

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'code', label: 'Código', field: 'code', align: 'left' as const },
  { name: 'cluster', label: 'Agrupamento', field: 'cluster_id', align: 'left' as const },
  { name: 'address', label: 'Morada', field: 'address', align: 'left' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const search = ref('')
const dialog = ref(false)
const editing = ref<null | { id: number }>(null)
const form = ref({ cluster_id: null as number | null, name: '', code: '', address: '' })

const clusterOptions = computed(() =>
  clustersStore.clusters.map((c) => ({ label: c.name, value: c.id }))
)

function clusterName(id: number) {
  return clustersStore.clusters.find((c) => c.id === id)?.name ?? '—'
}

onMounted(async () => {
  await Promise.all([schoolsStore.fetchAll(), clustersStore.fetchAll()])
})

function openCreate() {
  editing.value = null
  form.value = { cluster_id: null, name: '', code: '', address: '' }
  dialog.value = true
}

function openEdit(row: { id: number; cluster_id: number; name: string; code: string; address?: string }) {
  editing.value = row
  form.value = { cluster_id: row.cluster_id, name: row.name, code: row.code, address: row.address || '' }
  dialog.value = true
}

async function save() {
  if (!form.value.cluster_id) return
  try {
    const payload = { ...form.value, cluster_id: form.value.cluster_id }
    if (editing.value) {
      await schoolsStore.update(editing.value.id, payload)
      $q.notify({ type: 'positive', message: 'Escola atualizada' })
    } else {
      await schoolsStore.create(payload as { cluster_id: number; name: string; code: string })
      $q.notify({ type: 'positive', message: 'Escola criada' })
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
    await schoolsStore.remove(row.id)
    $q.notify({ type: 'positive', message: 'Eliminada' })
  })
}
</script>
