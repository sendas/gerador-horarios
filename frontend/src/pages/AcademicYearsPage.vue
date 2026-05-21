<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Anos Letivos</div>
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn color="primary" icon="add" label="Novo" @click="openCreate" class="q-ml-sm" />
    </div>

    <q-table :rows="store.years" :columns="columns" row-key="id" :loading="store.loading" :filter="search" sort-by="name">
      <template #body-cell-is_active="props">
        <q-td :props="props">
          <q-badge :color="props.row.is_active ? 'positive' : 'grey'" :label="props.row.is_active ? 'Ativo' : 'Inativo'" />
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn v-if="!props.row.is_active" unelevated size="sm" color="positive" icon="check_circle" label="Ativar" @click="activate(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openEdit(props.row)" class="q-mr-xs" />
          <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 450px">
        <q-card-section><div class="text-h6">{{ editing ? 'Editar' : 'Novo' }} Ano Letivo</div></q-card-section>
        <q-card-section>
          <q-form @submit="save">
            <q-select v-model="form.cluster_id" :options="clusterOptions" label="Agrupamento *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.name" label="Nome (ex: 2024/2025) *" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.start_date" label="Data início *" type="date" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.end_date" label="Data fim *" type="date" :rules="[v => !!v || 'Obrigatório']" />
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
import { useAcademicYearsStore } from 'stores/academicYears'
import { useClustersStore } from 'stores/clusters'

const $q = useQuasar()
const store = useAcademicYearsStore()
const clustersStore = useClustersStore()

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'start_date', label: 'Início', field: 'start_date', align: 'left' as const },
  { name: 'end_date', label: 'Fim', field: 'end_date', align: 'left' as const },
  { name: 'is_active', label: 'Estado', field: 'is_active', align: 'center' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const search = ref('')
const dialog = ref(false)
const editing = ref<null | { id: number }>(null)
const form = ref({ cluster_id: null as number | null, name: '', start_date: '', end_date: '' })

const clusterOptions = computed(() => clustersStore.clusters.map((c) => ({ label: c.name, value: c.id })))

onMounted(async () => {
  await Promise.all([store.fetchAll(), clustersStore.fetchAll()])
})

function openCreate() {
  editing.value = null
  form.value = { cluster_id: null, name: '', start_date: '', end_date: '' }
  dialog.value = true
}

function openEdit(row: { id: number; cluster_id: number; name: string; start_date: string; end_date: string }) {
  editing.value = row
  form.value = { cluster_id: row.cluster_id, name: row.name, start_date: row.start_date, end_date: row.end_date }
  dialog.value = true
}

async function save() {
  if (!form.value.cluster_id) return
  try {
    const payload = { ...form.value, cluster_id: form.value.cluster_id, is_active: false }
    if (editing.value) {
      await store.update(editing.value.id, payload)
      $q.notify({ type: 'positive', message: 'Atualizado' })
    } else {
      await store.create(payload as Parameters<typeof store.create>[0])
      $q.notify({ type: 'positive', message: 'Criado' })
    }
    dialog.value = false
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar' })
  }
}

async function activate(row: { id: number }) {
  await store.activate(row.id)
  $q.notify({ type: 'positive', message: 'Ano letivo ativado' })
}

function confirmDelete(row: { id: number; name: string }) {
  $q.dialog({
    title: 'Confirmar eliminação',
    message: `Eliminar "${row.name}"?`,
    ok: { label: 'Eliminar', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    await store.remove(row.id)
    $q.notify({ type: 'positive', message: 'Eliminado' })
  })
}
</script>
