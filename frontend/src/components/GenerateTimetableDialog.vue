<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" persistent>
    <q-card style="min-width:600px;max-width:760px">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6"><q-icon name="auto_awesome" class="q-mr-sm" />Gerar Horário</div>
        <q-space /><q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section class="q-gutter-md">

        <!-- ── Scope: schools ─────────────────────────────────────── -->
        <div v-if="clusterSchools.length > 1">
          <div class="row items-center q-mb-xs q-gutter-xs">
            <span class="text-subtitle2">Escolas</span>
            <q-chip
              v-for="s in clusterSchools" :key="s.id"
              clickable dense square
              :color="selectedSchoolIds.has(s.id) ? 'primary' : 'grey-3'"
              :text-color="selectedSchoolIds.has(s.id) ? 'white' : 'dark'"
              :icon="selectedSchoolIds.has(s.id) ? 'check' : undefined"
              @click="toggleSchool(s.id)"
            >{{ s.name }}</q-chip>
            <q-btn v-if="selectedSchoolIds.size > 0" flat dense size="xs" icon="clear" color="grey-6"
              @click="selectedSchoolIds.clear(); resetIndividual()" />
          </div>
        </div>

        <!-- ── Scope: year levels ─────────────────────────────────── -->
        <div>
          <div class="row items-center q-mb-xs q-gutter-xs">
            <span class="text-subtitle2">Anos de escolaridade</span>
            <q-chip
              v-for="yl in availableYearLevels" :key="yl"
              clickable dense square
              :color="selectedYearLevels.has(yl) ? 'indigo-6' : 'grey-3'"
              :text-color="selectedYearLevels.has(yl) ? 'white' : 'dark'"
              :icon="selectedYearLevels.has(yl) ? 'check' : undefined"
              @click="toggleYear(yl)"
            >{{ yl }}.º</q-chip>
            <q-btn v-if="selectedYearLevels.size > 0" flat dense size="xs" icon="clear" color="grey-6"
              @click="selectedYearLevels.clear(); resetIndividual()" />
          </div>
        </div>

        <!-- ── Scope: individual classes ─────────────────────────── -->
        <q-expansion-item
          v-model="showIndividual"
          icon="group" label="Turmas individuais" header-class="q-px-none"
          dense
        >
          <div class="q-mt-sm q-ml-sm">
            <div class="row items-center q-mb-xs q-gutter-xs">
              <q-btn flat dense size="xs" icon="select_all" label="Todas" color="teal" @click="selectAllFiltered" />
              <q-btn flat dense size="xs" icon="deselect" label="Nenhuma" color="grey-6" @click="individualClassIds.clear()" />
              <q-space />
              <q-chip dense icon="group" color="teal" text-color="white" size="sm"
                :label="`${effectiveCount} turmas`" />
            </div>
            <div v-if="loadingClasses" class="text-grey-6 text-caption q-py-sm">A carregar turmas...</div>
            <div v-else class="row q-gutter-xs flex-wrap">
              <template v-for="group in classGroups" :key="group.school_id">
                <div class="full-width text-caption text-grey-6 q-mt-xs q-mb-none">{{ group.school_name }}</div>
                <q-chip
                  v-for="cls in group.classes" :key="cls.id"
                  clickable dense square size="sm"
                  :color="individualClassIds.has(cls.id) ? 'teal' : 'grey-3'"
                  :text-color="individualClassIds.has(cls.id) ? 'white' : 'dark'"
                  @click="toggleIndividual(cls.id)"
                >{{ cls.name }}</q-chip>
              </template>
            </div>
          </div>
        </q-expansion-item>

        <!-- Summary -->
        <div class="row items-center q-gutter-sm">
          <q-chip dense icon="school" :color="effectiveCount === totalClasses ? 'grey-5' : 'teal'" text-color="white"
            :label="effectiveCount === totalClasses ? 'Todas as turmas' : `${effectiveCount} de ${totalClasses} turmas`" />
          <span v-if="effectiveCount === 0" class="text-negative text-caption">Nenhuma turma selecionada</span>
        </div>

        <q-separator />

        <!-- ── Constraints ────────────────────────────────────────── -->
        <div class="text-subtitle2">Alunos</div>
        <q-toggle v-model="opts.no_student_gaps" label="Sem furos nos horários dos alunos (restrição rígida)" />
        <q-toggle v-model="opts.students_start_slot_1" label="Alunos entram sempre no 1.º tempo (restrição rígida)" />
        <q-toggle v-model="opts.no_pe_after_lunch" label="Educação Física nunca depois do almoço" />

        <q-separator />

        <div class="text-subtitle2">Professores</div>
        <q-toggle v-model="opts.minimize_teacher_gaps" label="Maximizar tempos consecutivos dos professores" />
        <div v-if="opts.minimize_teacher_gaps" class="row items-center q-gutter-sm q-ml-lg">
          <span class="text-caption text-grey-7">Intensidade:</span>
          <q-btn-toggle
            v-model="opts.teacher_gap_weight"
            :options="[{label:'Suave',value:5},{label:'Médio',value:15},{label:'Forte',value:30},{label:'Máximo',value:60}]"
            color="primary" outline dense size="sm"
          />
        </div>

        <q-separator />

        <div class="text-subtitle2">Distribuição de disciplinas</div>
        <q-toggle v-model="opts.no_same_subject_twice_per_day" label="Máximo 1 tempo por disciplina por dia" />
        <q-toggle :model-value="opts.distribute_subjects_weight > 0" @update:model-value="opts.distribute_subjects_weight = $event ? 5 : 0" label="Distribuir disciplinas ao longo da semana" />

        <q-separator />

        <div class="text-subtitle2">Tempo máximo de cálculo</div>
        <div class="row q-gutter-xs flex-wrap">
          <q-btn
            v-for="opt in timeOptions" :key="opt.value"
            :label="opt.label"
            :color="opts.max_time_seconds === opt.value ? 'primary' : 'grey-4'"
            :text-color="opts.max_time_seconds === opt.value ? 'white' : 'dark'"
            unelevated dense size="sm"
            @click="opts.max_time_seconds = opt.value"
          />
        </div>
        <div class="text-caption text-grey-6 q-mt-xs">
          <q-icon name="info" size="xs" /> Tempos mais longos dão melhores resultados mas consomem mais recursos.
          Para agrupamentos grandes, recomenda-se 1h ou mais.
        </div>

      </q-card-section>

      <q-card-actions align="right" class="q-px-md q-pb-md">
        <q-btn flat label="Cancelar" v-close-popup />
        <q-btn color="primary" icon="play_arrow" label="Gerar Horário"
          :loading="loading" :disable="effectiveCount === 0"
          @click="generate" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useSchoolsStore } from 'stores/schools'
import { useClassesStore } from 'stores/classes'
import { useClustersStore } from 'stores/clusters'
import { useTimetablesStore } from 'stores/timetables'

const props = defineProps<{ modelValue: boolean; timetableId: number | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'started'): void
}>()

const $q = useQuasar()
const schoolsStore = useSchoolsStore()
const classesStore = useClassesStore()
const clustersStore = useClustersStore()
const timetablesStore = useTimetablesStore()
const loading = ref(false)
const loadingClasses = ref(false)
const showIndividual = ref(false)

const opts = reactive({
  no_student_gaps: true,
  students_start_slot_1: true,
  no_pe_after_lunch: true,
  minimize_teacher_gaps: true,
  teacher_gap_weight: 15,
  no_same_subject_twice_per_day: true,
  distribute_subjects_weight: 5,
  max_time_seconds: 300,
})

const timeOptions = [
  { label: '1 min',  value: 60 },
  { label: '2 min',  value: 120 },
  { label: '5 min',  value: 300 },
  { label: '10 min', value: 600 },
  { label: '30 min', value: 1800 },
  { label: '1h',     value: 3600 },
  { label: '2h',     value: 7200 },
  { label: '3h',     value: 10800 },
  { label: '5h',     value: 18000 },
  { label: '10h',    value: 36000 },
]

// ── Scope state ───────────────────────────────────────────────────────────────
const selectedSchoolIds = reactive(new Set<number>())
const selectedYearLevels = reactive(new Set<number>())
const individualClassIds = reactive(new Set<number>())
const individualInitialized = ref(false)

const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)

const clusterSchools = computed(() =>
  schoolsStore.schools.filter((s) => s.cluster_id === clusterId.value)
)

const academicYearId = computed(() =>
  timetablesStore.timetables.find((t) => t.id === props.timetableId)?.academic_year_id ?? null
)

// All classes for this timetable's academic year, belonging to cluster schools
const clusterSchoolIds = computed(() => new Set(clusterSchools.value.map((s) => s.id)))

const allYearClasses = computed(() =>
  classesStore.classes.filter(
    (c) => c.academic_year_id === academicYearId.value && clusterSchoolIds.value.has(c.school_id)
  )
)

const totalClasses = computed(() => allYearClasses.value.length)

const availableYearLevels = computed(() =>
  [...new Set(allYearClasses.value.map((c) => c.year_level))].sort((a, b) => a - b)
)

// Classes matching current school + year filters
const filteredClasses = computed(() =>
  allYearClasses.value.filter((c) => {
    if (selectedSchoolIds.size > 0 && !selectedSchoolIds.has(c.school_id)) return false
    if (selectedYearLevels.size > 0 && !selectedYearLevels.has(c.year_level)) return false
    return true
  })
)

// Individual-mode class IDs: use explicit set only if initialized AND user opened the section
const useIndividual = computed(() => individualInitialized.value && showIndividual.value)

// How many classes will actually be generated
const effectiveCount = computed(() => {
  if (useIndividual.value) return individualClassIds.size
  return filteredClasses.value.length
})

// class_ids to send (null = all for the solver)
const effectiveClassIds = computed((): number[] | null => {
  if (useIndividual.value) return [...individualClassIds]
  // if filtered == all, send null
  if (filteredClasses.value.length === totalClasses.value) return null
  return filteredClasses.value.map((c) => c.id)
})

// Classes grouped by school for the individual picker
const classGroups = computed(() => {
  const bySchool = new Map<number, typeof filteredClasses.value>()
  for (const c of filteredClasses.value) {
    if (!bySchool.has(c.school_id)) bySchool.set(c.school_id, [])
    bySchool.get(c.school_id)!.push(c)
  }
  return [...bySchool.entries()].map(([schoolId, classes]) => ({
    school_id: schoolId,
    school_name: schoolsStore.schools.find((s) => s.id === schoolId)?.name ?? '—',
    classes: classes.sort((a, b) => a.year_level - b.year_level || a.name.localeCompare(b.name)),
  })).sort((a, b) => a.school_name.localeCompare(b.school_name))
})

function toggleSchool(id: number) {
  if (selectedSchoolIds.has(id)) selectedSchoolIds.delete(id)
  else selectedSchoolIds.add(id)
  resetIndividual()
}

function toggleYear(yl: number) {
  if (selectedYearLevels.has(yl)) selectedYearLevels.delete(yl)
  else selectedYearLevels.add(yl)
  resetIndividual()
}

function toggleIndividual(id: number) {
  individualInitialized.value = true
  if (individualClassIds.has(id)) individualClassIds.delete(id)
  else individualClassIds.add(id)
}

function selectAllFiltered() {
  individualInitialized.value = true
  filteredClasses.value.forEach((c) => individualClassIds.add(c.id))
}

function resetIndividual() {
  individualClassIds.clear()
  individualInitialized.value = false
}

// When dialog opens, load data and reset state
watch(() => props.modelValue, async (open) => {
  if (!open) return
  resetIndividual()
  selectedSchoolIds.clear()
  selectedYearLevels.clear()
  showIndividual.value = false
  if (academicYearId.value && allYearClasses.value.length === 0) {
    loadingClasses.value = true
    try { await classesStore.fetchAll({ academic_year_id: academicYearId.value }) }
    finally { loadingClasses.value = false }
  }
  await Promise.all([
    schoolsStore.schools.length === 0 ? schoolsStore.fetchAll() : Promise.resolve(),
    clustersStore.clusters.length === 0 ? clustersStore.fetchAll() : Promise.resolve(),
  ])
})

async function generate() {
  if (!props.timetableId || effectiveCount.value === 0) return
  loading.value = true
  try {
    const classIds = effectiveClassIds.value
    await api.post(`/timetables/${props.timetableId}/generate`, {
      class_ids: classIds,
      // year_levels and school_ids already encoded in class_ids above
      no_student_gaps: opts.no_student_gaps,
      students_start_slot_1: opts.students_start_slot_1,
      no_pe_after_lunch: opts.no_pe_after_lunch,
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
