<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">
        <q-icon name="upload_file" class="q-mr-sm" />
        Importar Currículo
      </div>
    </div>

    <q-card style="max-width: 680px">
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
            :disable="loading"
            @update:model-value="selectedSchool = null; selectedYear = null"
          />

          <q-select
            v-model="selectedSchool"
            :options="schoolOptions"
            label="Escola *"
            outlined
            emit-value
            map-options
            :disable="!selectedCluster || loading"
            :rules="[(v) => !!v || 'Obrigatório']"
          />

          <q-select
            v-model="selectedYear"
            :options="yearOptions"
            label="Ano Letivo *"
            outlined
            emit-value
            map-options
            :disable="!selectedCluster || loading"
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

          <!-- Progress -->
          <div v-if="loading" class="q-mt-sm">
            <div class="row items-center q-mb-xs">
              <span class="text-caption col">{{ progressLabel }}</span>
              <span class="text-caption text-grey-6">{{ Math.round(progress * 100) }}%</span>
            </div>
            <q-linear-progress :value="progress" color="primary" rounded style="height: 10px" />
            <div class="text-caption text-grey-6 q-mt-xs">
              {{ progressStats }}
            </div>
          </div>

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
            <ul v-if="result.errors?.length" class="q-mt-xs q-mb-none" style="max-height:200px;overflow-y:auto">
              <li v-for="(e, i) in result.errors" :key="i" class="text-caption text-negative">{{ e }}</li>
            </ul>
          </q-banner>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="q-px-md q-pb-md">
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
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useClustersStore } from 'stores/clusters'
import { useSchoolsStore } from 'stores/schools'
import { useAcademicYearsStore } from 'stores/academicYears'

const $q = useQuasar()
const clustersStore = useClustersStore()
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()

const selectedCluster = ref<number | null>(null)
const selectedSchool = ref<number | null>(null)
const selectedYear = ref<number | null>(null)
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const progress = ref(0)
const progressProcessed = ref(0)
const progressTotal = ref(0)
const progressCreated = ref(0)
const progressSkipped = ref(0)

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

const progressLabel = computed(() =>
  progressTotal.value > 0
    ? `A processar linha ${progressProcessed.value} de ${progressTotal.value}…`
    : 'A processar…'
)

const progressStats = computed(() =>
  `Criadas: ${progressCreated.value}  |  Ignoradas: ${progressSkipped.value}`
)

async function upload() {
  if (!selectedFile.value || !selectedCluster.value || !selectedSchool.value || !selectedYear.value) return
  loading.value = true
  progress.value = 0
  progressProcessed.value = 0
  progressTotal.value = 0
  progressCreated.value = 0
  progressSkipped.value = 0
  result.value = null

  const fd = new FormData()
  fd.append('file', selectedFile.value)
  fd.append('cluster_id', String(selectedCluster.value))
  fd.append('school_id', String(selectedSchool.value))
  fd.append('academic_year_id', String(selectedYear.value))

  const token = localStorage.getItem('token')

  try {
    const response = await fetch('/api/v1/imports/curriculum/stream', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      $q.notify({ color: 'negative', message: (data as { detail?: string }).detail ?? 'Erro ao importar' })
      return
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.trim()) continue
        const update = JSON.parse(line) as {
          processed: number; total: number; created: number; skipped: number;
          new_classes: number; new_subjects: number; new_teachers: number;
          errors: string[]; done?: boolean
        }
        progressProcessed.value = update.processed
        progressTotal.value = update.total
        progressCreated.value = update.created
        progressSkipped.value = update.skipped
        progress.value = update.total > 0 ? update.processed / update.total : 0

        if (update.done) {
          result.value = {
            created: update.created,
            skipped: update.skipped,
            new_classes: update.new_classes,
            new_subjects: update.new_subjects,
            new_teachers: update.new_teachers,
            errors: update.errors,
          }
          $q.notify({ color: 'positive', message: `${update.created} entradas de currículo importadas` })
        }
      }
    }
  } catch (e: unknown) {
    $q.notify({ color: 'negative', message: 'Erro de ligação durante a importação' })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    clustersStore.fetchAll(),
    schoolsStore.fetchAll(),
    yearsStore.fetchAll(),
  ])
})
</script>
