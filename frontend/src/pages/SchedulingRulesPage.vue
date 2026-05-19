<template>
  <q-page padding>
    <div class="text-h5 q-mb-md">Regras de Horário</div>

    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-sm-6">
        <q-select
          v-model="selectedClusterId"
          :options="clusterOptions"
          label="Agrupamento *"
          emit-value
          map-options
          clearable
          @update:model-value="onClusterChange"
        />
      </div>
      <div class="col-12 col-sm-6">
        <q-select
          v-model="selectedYearId"
          :options="yearOptions"
          label="Ano Letivo (opcional — deixe vazio para regra global)"
          emit-value
          map-options
          clearable
          :disable="!selectedClusterId"
          @update:model-value="loadRules"
        />
      </div>
    </div>

    <template v-if="selectedClusterId">
      <q-banner v-if="!currentRule" class="bg-info text-white q-mb-md" rounded>
        <template #avatar><q-icon name="info" /></template>
        Não existem regras definidas para esta combinação. Clique em "Criar Regras" para definir.
      </q-banner>

      <q-card v-if="currentRule || showForm">
        <q-card-section>
          <div class="text-h6 q-mb-md">Limites de Tempos por Dia</div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.max_periods_per_day_class"
                label="Máx. tempos/dia por turma"
                type="number"
                min="1"
                max="12"
                outlined
                hint="Número máximo de tempos letivos que uma turma pode ter por dia."
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.max_periods_per_day_teacher"
                label="Máx. tempos/dia por professor"
                type="number"
                min="1"
                max="12"
                outlined
                hint="Número máximo de tempos letivos que um professor pode ter por dia."
              />
            </div>
          </div>

          <div class="text-h6 q-mb-md q-mt-lg">Limites de Tempos Consecutivos</div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.max_consecutive_periods_class"
                label="Máx. tempos consecutivos por turma"
                type="number"
                min="1"
                max="8"
                outlined
                hint="Número máximo de tempos consecutivos (sem intervalo) para uma turma."
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model.number="form.max_consecutive_periods_teacher"
                label="Máx. tempos consecutivos por professor"
                type="number"
                min="1"
                max="8"
                outlined
                hint="Número máximo de tempos consecutivos (sem intervalo) para um professor."
              />
            </div>
          </div>

          <div class="text-h6 q-mb-md q-mt-lg">Preferências de Distribuição</div>
          <q-toggle
            v-model="form.avoid_isolated_teacher"
            label="Evitar tempos isolados para professores"
            color="primary"
          />
          <div class="text-caption text-grey q-mt-xs q-ml-xl">
            Quando ativo, o sistema penaliza situações em que um professor tem apenas um tempo letivo isolado num dia,
            sem aulas adjacentes. Isto reduz deslocações desnecessárias.
          </div>

          <div class="text-h6 q-mb-md q-mt-lg">Restrições de Horário dos Alunos</div>
          <q-toggle
            v-model="form.no_student_gaps"
            label="Sem furos nos horários dos alunos"
            color="primary"
          />
          <div class="text-caption text-grey q-mt-xs q-ml-xl">
            Restrição rígida: as aulas de cada turma num dado dia devem ser contíguas (sem períodos livres entre elas).
          </div>

          <div class="text-h6 q-mb-md q-mt-lg">Entradas e Saídas dos Alunos</div>
          <q-toggle
            v-model="form.students_start_slot_1"
            label="Alunos entram sempre no 1.º tempo"
            color="primary"
          />
          <div class="text-caption text-grey q-mt-xs q-ml-xl">
            Restrição rígida: para cada turma, o primeiro tempo de cada dia deve ser sempre ocupado (sem entrar no 2.º tempo).
          </div>

          <q-separator class="q-my-md" />
          <div class="text-h6 q-mb-md">Educação Física</div>
          <q-toggle
            v-model="form.no_pe_after_lunch"
            label="Sem Educação Física depois do almoço"
            color="orange-7"
          />
          <div class="text-caption text-grey q-mt-xs q-ml-xl q-mb-sm">
            Restrição rígida: disciplinas marcadas como 'Educação Física' não podem ser agendadas após o almoço.
          </div>
          <q-input
            v-if="form.no_pe_after_lunch"
            v-model.number="form.lunch_after_slot"
            label="Último tempo antes do almoço"
            type="number"
            min="1"
            max="10"
            outlined
            style="max-width: 220px"
            hint="Número do tempo letivo após o qual começa o período de almoço (ex: 4)."
          />

          <div class="text-h6 q-mb-md q-mt-lg">Restrições de Horário dos Professores</div>
          <q-toggle
            v-model="form.minimize_teacher_gaps"
            label="Minimizar furos dos professores"
            color="primary"
          />
          <div class="text-caption text-grey q-mt-xs q-ml-xl q-mb-sm">
            Soft: penaliza períodos livres entre aulas de um professor no mesmo dia.
          </div>
          <q-input
            v-if="form.minimize_teacher_gaps"
            v-model.number="form.teacher_gap_weight"
            label="Peso dos furos de professor"
            type="number"
            min="1"
            max="50"
            outlined
            style="max-width: 200px"
            hint="Penalização por cada furo (1–50)."
          />

          <div class="text-h6 q-mb-md q-mt-lg">Distribuição de Disciplinas</div>
          <q-toggle
            v-model="form.no_same_subject_twice_per_day"
            label="Máximo 1 tempo por disciplina por dia"
            color="primary"
          />
          <div class="text-caption text-grey q-mt-xs q-ml-xl q-mb-sm">
            Restrição rígida: uma turma não pode ter a mesma disciplina duas vezes no mesmo dia.
          </div>
          <q-input
            v-model.number="form.distribute_subjects_weight"
            label="Peso da distribuição semanal de disciplinas"
            type="number"
            min="0"
            max="20"
            outlined
            style="max-width: 220px"
            hint="Penalização por disciplina repetida no mesmo dia (0 = desligado)."
          />
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn
            v-if="!currentRule"
            color="primary"
            icon="add"
            label="Criar Regras"
            :loading="saving"
            @click="saveRules"
          />
          <q-btn
            v-else
            color="primary"
            icon="save"
            label="Guardar Alterações"
            :loading="saving"
            @click="saveRules"
          />
        </q-card-actions>
      </q-card>

      <q-btn
        v-if="!currentRule && !showForm"
        color="primary"
        icon="add"
        label="Criar Regras"
        class="q-mt-md"
        @click="showForm = true"
      />

      <q-card :class="$q.dark.isActive ? 'bg-blue-9' : 'bg-blue-1'" flat bordered v-if="currentRule">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm"><q-icon name="help_outline" class="q-mr-sm" />O que significam estas regras?</div>
          <q-list dense>
            <q-item>
              <q-item-section avatar><q-icon name="groups" color="primary" /></q-item-section>
              <q-item-section>
                <q-item-label><strong>Máx. tempos/dia por turma:</strong> Impede que uma turma tenha mais do que N aulas num único dia.</q-item-label>
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section avatar><q-icon name="person" color="primary" /></q-item-section>
              <q-item-section>
                <q-item-label><strong>Máx. tempos/dia por professor:</strong> Combina com o limite individual do professor (usa o menor valor).</q-item-label>
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section avatar><q-icon name="view_week" color="primary" /></q-item-section>
              <q-item-section>
                <q-item-label><strong>Máx. tempos consecutivos por turma:</strong> Garante pausas entre blocos de aulas para os alunos.</q-item-label>
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section avatar><q-icon name="timer" color="primary" /></q-item-section>
              <q-item-section>
                <q-item-label><strong>Máx. tempos consecutivos por professor:</strong> Evita que professores ensinem muitas horas seguidas sem pausa.</q-item-label>
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section avatar><q-icon name="alt_route" color="primary" /></q-item-section>
              <q-item-section>
                <q-item-label><strong>Evitar tempos isolados:</strong> Reduz situações em que um professor se desloca à escola apenas para uma aula isolada.</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </template>

    <template v-else>
      <q-banner :class="$q.dark.isActive ? 'bg-grey-8' : 'bg-grey-2'" rounded>
        <template #avatar><q-icon name="arrow_upward" color="grey" /></template>
        Selecione um agrupamento para ver ou editar as regras de horário.
      </q-banner>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useClustersStore } from 'stores/clusters'
import { useAcademicYearsStore } from 'stores/academicYears'

interface SchedulingRulesResponse {
  id: number
  cluster_id: number
  academic_year_id: number | null
  max_periods_per_day_class: number
  max_periods_per_day_teacher: number
  max_consecutive_periods_class: number
  max_consecutive_periods_teacher: number
  avoid_isolated_teacher: boolean
  no_student_gaps: boolean
  minimize_teacher_gaps: boolean
  teacher_gap_weight: number
  no_same_subject_twice_per_day: boolean
  distribute_subjects_weight: number
  students_start_slot_1: boolean
  no_pe_after_lunch: boolean
  lunch_after_slot: number
}

const $q = useQuasar()
const clustersStore = useClustersStore()
const yearsStore = useAcademicYearsStore()

const selectedClusterId = ref<number | null>(null)
const selectedYearId = ref<number | null>(null)
const currentRule = ref<SchedulingRulesResponse | null>(null)
const showForm = ref(false)
const saving = ref(false)

const defaultForm = () => ({
  max_periods_per_day_class: 5,
  max_periods_per_day_teacher: 6,
  max_consecutive_periods_class: 2,
  max_consecutive_periods_teacher: 4,
  avoid_isolated_teacher: false,
  no_student_gaps: true,
  minimize_teacher_gaps: true,
  teacher_gap_weight: 10,
  no_same_subject_twice_per_day: true,
  distribute_subjects_weight: 5,
  students_start_slot_1: true,
  no_pe_after_lunch: true,
  lunch_after_slot: 4,
})

const form = ref(defaultForm())

const clusterOptions = computed(() =>
  clustersStore.clusters.map((c) => ({ label: c.name, value: c.id }))
)

const yearOptions = computed(() => {
  const filtered = selectedClusterId.value
    ? yearsStore.years.filter((y) => y.cluster_id === selectedClusterId.value)
    : yearsStore.years
  return filtered.map((y) => ({ label: y.name, value: y.id }))
})

onMounted(async () => {
  await Promise.all([clustersStore.fetchAll(), yearsStore.fetchAll()])
})

async function onClusterChange() {
  selectedYearId.value = null
  currentRule.value = null
  showForm.value = false
  form.value = defaultForm()
  if (selectedClusterId.value) {
    await loadRules()
  }
}

async function loadRules() {
  if (!selectedClusterId.value) return
  try {
    const params: Record<string, number> = { cluster_id: selectedClusterId.value }
    const { data } = await api.get<SchedulingRulesResponse[]>('/scheduling-rules', { params })
    // Find most specific rule: prefer year-specific, fall back to global
    const yearSpecific = selectedYearId.value
      ? data.find((r) => r.academic_year_id === selectedYearId.value)
      : null
    const global = data.find((r) => r.academic_year_id === null)
    currentRule.value = yearSpecific ?? global ?? null

    if (currentRule.value) {
      form.value = {
        max_periods_per_day_class: currentRule.value.max_periods_per_day_class,
        max_periods_per_day_teacher: currentRule.value.max_periods_per_day_teacher,
        max_consecutive_periods_class: currentRule.value.max_consecutive_periods_class,
        max_consecutive_periods_teacher: currentRule.value.max_consecutive_periods_teacher,
        avoid_isolated_teacher: currentRule.value.avoid_isolated_teacher,
        no_student_gaps: currentRule.value.no_student_gaps,
        minimize_teacher_gaps: currentRule.value.minimize_teacher_gaps,
        teacher_gap_weight: currentRule.value.teacher_gap_weight,
        no_same_subject_twice_per_day: currentRule.value.no_same_subject_twice_per_day,
        distribute_subjects_weight: currentRule.value.distribute_subjects_weight,
        students_start_slot_1: currentRule.value.students_start_slot_1 ?? true,
        no_pe_after_lunch: currentRule.value.no_pe_after_lunch ?? true,
        lunch_after_slot: currentRule.value.lunch_after_slot ?? 4,
      }
      showForm.value = true
    } else {
      form.value = defaultForm()
      showForm.value = false
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao carregar regras' })
  }
}

async function saveRules() {
  if (!selectedClusterId.value) return
  saving.value = true
  try {
    if (currentRule.value) {
      const { data } = await api.put<SchedulingRulesResponse>(
        `/scheduling-rules/${currentRule.value.id}`,
        form.value
      )
      currentRule.value = data
      $q.notify({ type: 'positive', message: 'Regras atualizadas com sucesso' })
    } else {
      const payload = {
        cluster_id: selectedClusterId.value,
        academic_year_id: selectedYearId.value ?? null,
        ...form.value,
      }
      const { data } = await api.post<SchedulingRulesResponse>('/scheduling-rules', payload)
      currentRule.value = data
      showForm.value = true
      $q.notify({ type: 'positive', message: 'Regras criadas com sucesso' })
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar regras' })
  } finally {
    saving.value = false
  }
}
</script>
