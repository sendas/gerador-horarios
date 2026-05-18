<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" persistent>
    <q-card style="min-width: 560px; max-width: 700px">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6"><q-icon name="auto_awesome" class="q-mr-sm"/>Gerar Horário</div>
        <q-space/><q-btn icon="close" flat round dense v-close-popup/>
      </q-card-section>

      <q-card-section class="q-gutter-md">
        <!-- Ciclos -->
        <div class="text-subtitle2 q-mb-xs">Ciclos a incluir</div>
        <div class="row q-gutter-sm">
          <q-toggle v-model="opts.include2ndCycle" label="2.° Ciclo (5.°-6.° ano)" />
          <q-toggle v-model="opts.include3rdCycle" label="3.° Ciclo (7.°-9.° ano)" />
          <q-toggle v-model="opts.includeSecondary" label="Secundário (10.°-12.° ano)" />
        </div>

        <q-separator/>

        <!-- Restrições alunos -->
        <div class="text-subtitle2">Alunos</div>
        <q-toggle v-model="opts.no_student_gaps" label="Sem furos nos horários dos alunos (restrição rígida)" />

        <q-separator/>

        <!-- Professores -->
        <div class="text-subtitle2">Professores</div>
        <q-toggle v-model="opts.minimize_teacher_gaps" label="Minimizar furos nos horários dos professores" />
        <q-slider v-if="opts.minimize_teacher_gaps" v-model="opts.teacher_gap_weight" :min="1" :max="50" label :label-value="'Peso: ' + opts.teacher_gap_weight" />

        <q-separator/>

        <!-- Distribuição -->
        <div class="text-subtitle2">Distribuição de disciplinas</div>
        <q-toggle v-model="opts.no_same_subject_twice_per_day" label="Máximo 1 tempo por disciplina por dia" />
        <q-toggle :model-value="opts.distribute_subjects_weight > 0" @update:model-value="opts.distribute_subjects_weight = $event ? 5 : 0" label="Distribuir disciplinas ao longo da semana" />

        <q-separator/>

        <!-- Tempo de cálculo -->
        <div class="text-subtitle2">Tempo máximo de cálculo</div>
        <div class="row items-center q-gutter-md">
          <q-btn-toggle v-model="opts.max_time_seconds" :options="[{label:'1 min',value:60},{label:'2 min',value:120},{label:'5 min',value:300},{label:'10 min',value:600}]" />
        </div>
      </q-card-section>

      <q-card-actions align="right" class="q-px-md q-pb-md">
        <q-btn flat label="Cancelar" v-close-popup/>
        <q-btn color="primary" icon="play_arrow" label="Gerar Horário" :loading="loading" @click="generate"/>
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

const props = defineProps<{ modelValue: boolean; timetableId: number | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'started'): void
}>()

const $q = useQuasar()
const loading = ref(false)

const opts = reactive({
  include2ndCycle: true,
  include3rdCycle: true,
  includeSecondary: true,
  no_student_gaps: true,
  minimize_teacher_gaps: true,
  teacher_gap_weight: 10,
  no_same_subject_twice_per_day: true,
  distribute_subjects_weight: 5,
  max_time_seconds: 120,
})

async function generate() {
  if (!props.timetableId) return
  loading.value = true
  try {
    const year_levels: number[] = []
    if (opts.include2ndCycle) year_levels.push(5, 6)
    if (opts.include3rdCycle) year_levels.push(7, 8, 9)
    if (opts.includeSecondary) year_levels.push(10, 11, 12)

    await api.post(`/timetables/${props.timetableId}/generate`, {
      year_levels: year_levels.length === 0 ? null : year_levels,
      no_student_gaps: opts.no_student_gaps,
      minimize_teacher_gaps: opts.minimize_teacher_gaps,
      teacher_gap_weight: opts.teacher_gap_weight,
      no_same_subject_twice_per_day: opts.no_same_subject_twice_per_day,
      distribute_subjects_weight: opts.distribute_subjects_weight,
      max_time_seconds: opts.max_time_seconds,
    })
    $q.notify({ color: 'positive', message: 'Geração iniciada em segundo plano' })
    emit('started')
    emit('update:modelValue', false)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    $q.notify({ color: 'negative', message: err.response?.data?.detail ?? 'Erro ao iniciar geração' })
  } finally {
    loading.value = false
  }
}
</script>
