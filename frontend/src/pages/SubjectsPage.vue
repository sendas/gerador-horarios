<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Disciplinas</div>
      <q-btn color="primary" icon="add" label="Nova" @click="openCreate" />
    </div>

    <q-table :rows="subjectsStore.subjects" :columns="columns" row-key="id" :loading="subjectsStore.loading">
      <template #body-cell-color="props">
        <q-td :props="props">
          <div style="width:24px;height:24px;border-radius:4px;display:inline-block" :style="{ background: props.row.color }" />
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn flat round dense icon="edit" @click="openEdit(props.row)" />
          <q-btn flat round dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 400px">
        <q-card-section><div class="text-h6">{{ editing ? 'Editar' : 'Nova' }} Disciplina</div></q-card-section>
        <q-card-section>
          <q-form @submit="save">
            <q-select v-model="form.cluster_id" :options="clusterOptions" label="Agrupamento *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.name" label="Nome *" :rules="[v => !!v || 'Obrigatório']" />
            <q-input v-model="form.code" label="Código (abreviatura)" />
            <div class="q-mt-sm">
              <label class="text-caption">Cor</label>
              <div class="row q-gutter-xs q-mt-xs">
                <div
                  v-for="c in colorPalette"
                  :key="c"
                  :style="{ background: c, width: '28px', height: '28px', borderRadius: '4px', cursor: 'pointer', border: form.color === c ? '3px solid #333' : '2px solid transparent' }"
                  @click="form.color = c"
                />
              </div>
            </div>
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
import { useSubjectsStore } from 'stores/subjects'
import { useClustersStore } from 'stores/clusters'

const $q = useQuasar()
const subjectsStore = useSubjectsStore()
const clustersStore = useClustersStore()

const colorPalette = [
  '#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6',
  '#1abc9c', '#e67e22', '#34495e', '#e91e63', '#00bcd4',
  '#8bc34a', '#ff5722', '#607d8b', '#795548', '#ff9800',
]

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'code', label: 'Código', field: 'code', align: 'left' as const },
  { name: 'color', label: 'Cor', field: 'color', align: 'center' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const dialog = ref(false)
const editing = ref<null | { id: number }>(null)
const form = ref({ cluster_id: null as number | null, name: '', code: '', color: '#3498db' })

const clusterOptions = computed(() => clustersStore.clusters.map((c) => ({ label: c.name, value: c.id })))

onMounted(async () => {
  await Promise.all([subjectsStore.fetchAll(), clustersStore.fetchAll()])
})

function openCreate() {
  editing.value = null
  form.value = { cluster_id: null, name: '', code: '', color: '#3498db' }
  dialog.value = true
}

function openEdit(row: { id: number; cluster_id: number; name: string; code?: string; color: string }) {
  editing.value = row
  form.value = { cluster_id: row.cluster_id, name: row.name, code: row.code || '', color: row.color }
  dialog.value = true
}

async function save() {
  if (!form.value.cluster_id) return
  try {
    if (editing.value) {
      await subjectsStore.update(editing.value.id, form.value)
      $q.notify({ type: 'positive', message: 'Atualizada' })
    } else {
      await subjectsStore.create(form.value as { cluster_id: number; name: string; color: string })
      $q.notify({ type: 'positive', message: 'Criada' })
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
    await subjectsStore.remove(row.id)
    $q.notify({ type: 'positive', message: 'Eliminada' })
  })
}
</script>
