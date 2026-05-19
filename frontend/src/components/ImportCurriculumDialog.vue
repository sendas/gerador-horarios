<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" persistent>
    <q-card style="min-width: 520px; max-width: 640px; width: 100%">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">
          <q-icon name="upload_file" class="q-mr-sm" />
          Importar Currículo Completo
        </div>
        <q-space />
        <q-btn icon="close" flat round dense @click="close" />
      </q-card-section>

      <q-card-section>
        <q-banner :class="$q.dark.isActive ? 'bg-blue-9' : 'bg-blue-1'" class="q-mb-md" rounded>
          <template #avatar><q-icon name="info" color="blue" /></template>
          Importa turmas, disciplinas, professores e o currículo completo a partir de um ficheiro CSV/Excel.
          <br /><br />
          <strong>Colunas esperadas:</strong>
          <code>ano</code>, <code>turma</code>, <code>disciplina</code>,
          <code>horas semana</code>, <code>ano+turma+disc</code> (ignorada), <code>professor</code>, <code>articulado</code>
          <br /><br />
          <strong>Campo <code>articulado</code>:</strong>
          <ul class="q-mb-none q-mt-xs" style="padding-left:1.2em">
            <li><em>Vazio</em> — sem articulado</li>
            <li><em>"sim"</em> — disciplina pode ter dispensa (articulado)</li>
            <li><em>Outro valor</em> — texto guardado nas observações da turma</li>
          </ul>
        </q-banner>

        <div class="q-gutter-md">
          <q-select
            v-model="selectedCluster"
            :options="clusterOptions"
            label="Agrupamento *"
            outlined
            emit-value
            map-options
            :rules="[(v) => !!v || 'Obrigatório']"
            @update:model-value="selectedSchool = null; selectedYear = null"
          />

          <q-select
            v-model="selectedSchool"
            :options="schoolOptions"
            label="Escola *"
            outlined
            emit-value
            map-options
            :disable="!selectedCluster"
            :rules="[(v) => !!v || 'Obrigatório']"
          />

          <q-select
            v-model="selectedYear"
            :options="yearOptions"
            label="Ano Letivo *"
            outlined
            emit-value
            map-options
            :disable="!selectedCluster"
            :rules="[(v) => !!v || 'Obrigatório']"
          />

          <q-file
            v-model="selectedFile"
            label="Ficheiro CSV ou Excel"
            outlined
            accept=".csv,.xlsx,.xls"
            :disable="loading"
          >
            <template #prepend><q-icon name="attach_file" /></template>
          </q-file>

          <q-banner v-if="result" rounded :class="result.errors?.length ? ($q.dark.isActive ? 'bg-orange-9' : 'bg-orange-1') : ($q.dark.isActive ? 'bg-green-9' : 'bg-green-1')">
            <template #avatar>
              <q-icon :name="result.errors?.length ? 'warning' : 'check_circle'" :color="result.errors?.length ? 'warning' : 'positive'" />
            </template>
            <div class="text-weight-medium q-mb-xs">Importação concluída</div>
            <div class="text-body2">
              Entradas de currículo criadas: <strong>{{ result.created }}</strong><br />
              Ignoradas (já existiam): <strong>{{ result.skipped }}</strong><br />
              Turmas novas: <strong>{{ result.new_classes }}</strong> &nbsp;
              Disciplinas novas: <strong>{{ result.new_subjects }}</strong> &nbsp;
              Professores novos: <strong>{{ result.new_teachers }}</strong>
            </div>
            <ul v-if="result.errors?.length" class="q-mt-xs q-mb-none">
              <li v-for="(e, i) in result.errors" :key="i" class="text-caption text-negative">{{ e }}</li>
            </ul>
          </q-banner>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="q-px-md q-pb-md">
        <q-btn flat label="Fechar" @click="close" />
        <q-btn
          color="primary"
          icon="upload"
          label="Importar"
          :loading="loading"
          :disable="!selectedFile || !selectedCluster || !selectedSchool || !selectedYear"
          @click="upload"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useClustersStore } from 'stores/clusters'
import { useSchoolsStore } from 'stores/schools'
import { useAcademicYearsStore } from 'stores/academicYears'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'done'): void
}>()

const $q = useQuasar()
const clustersStore = useClustersStore()
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()

const selectedCluster = ref<number | null>(null)
const selectedSchool = ref<number | null>(null)
const selectedYear = ref<number | null>(null)
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const result = ref<{
  created: number; skipped: number; new_classes: number;
  new_subjects: number; new_teachers: number; errors: string[]
} | null>(null)

const clusterOptions = computed(() =>
  clustersStore.clusters.map((c) => ({ label: c.name, value: c.id }))
)
const schoolOptions = computed(() =>
  schoolsStore.schools
    .filter((s) => !selectedCluster.value || s.cluster_id === selectedCluster.value)
    .map((s) => ({ label: s.name, value: s.id }))
)
const yearOptions = computed(() =>
  yearsStore.years
    .filter((y) => !selectedCluster.value || y.cluster_id === selectedCluster.value)
    .map((y) => ({ label: y.name, value: y.id }))
)

async function upload() {
  if (!selectedFile.value || !selectedCluster.value || !selectedSchool.value || !selectedYear.value) return
  loading.value = true
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    fd.append('cluster_id', String(selectedCluster.value))
    fd.append('school_id', String(selectedSchool.value))
    fd.append('academic_year_id', String(selectedYear.value))
    const { data } = await api.post('/imports/curriculum', fd)
    result.value = data
    $q.notify({ color: 'positive', message: `${data.created} entradas de currículo importadas` })
    emit('done')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    $q.notify({ color: 'negative', message: err.response?.data?.detail ?? 'Erro ao importar' })
  } finally {
    loading.value = false
  }
}

function close() {
  result.value = null
  selectedFile.value = null
  emit('update:modelValue', false)
}

onMounted(async () => {
  await Promise.all([
    clustersStore.fetchAll(),
    schoolsStore.fetchAll(),
    yearsStore.fetchAll(),
  ])
})
</script>
