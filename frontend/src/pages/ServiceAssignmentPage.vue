<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Distribuição de Serviço</div>
      <q-btn color="teal-7" icon="tune" label="Gerir horas" class="q-mr-sm" @click="openHoursDialog" />
      <q-btn color="indigo-7" icon="calculate" label="Componentes" class="q-mr-sm" :disable="!selectedYearId" @click="openComponentDialog" />
      <q-select
        v-model="selectedYearId"
        :options="yearOptions"
        label="Ano Letivo"
        emit-value map-options
        dense outlined
        style="min-width:200px"
        @update:model-value="onYearChange"
      />
    </div>

    <div v-if="!selectedYearId" class="text-center text-grey q-pa-xl">
      <q-icon name="calendar_today" size="64px" color="grey-3" />
      <div class="q-mt-sm">Selecione um ano letivo para começar</div>
    </div>

    <div v-else class="row q-col-gutter-md">

      <!-- ── Left panel: teacher + hours ─────────────────── -->
      <div class="col-12 col-md-3">

        <!-- Teacher select -->
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey-7 q-mb-xs">PROFESSOR</div>
            <q-select
              v-model="selectedTeacherId"
              :options="filteredTeacherOptions"
              label="Escolher professor..."
              emit-value map-options
              dense outlined
              use-input
              input-debounce="0"
              @filter="filterTeachersFn"
              @update:model-value="onTeacherChange"
            />
          </q-card-section>

          <!-- Hours counter -->
          <template v-if="selectedTeacherId && selectedTeacher">
            <q-separator />
            <q-card-section class="text-center q-pb-xs">
              <div
                class="text-h2 text-weight-bold"
                :class="remainingHours < 0 ? 'text-negative' : remainingHours === 0 ? 'text-positive' : 'text-primary'"
              >
                {{ remainingHours }}h
              </div>
              <div class="text-caption text-grey">horas livres</div>
            </q-card-section>

            <q-card-section class="q-pt-xs">
              <q-linear-progress
                :value="progressRatio"
                :color="progressColor"
                track-color="grey-3"
                size="12px"
                rounded
                class="q-mb-sm"
              />
              <div class="row text-center q-gutter-none">
                <div class="col">
                  <div class="text-subtitle2">{{ totalHours }}h</div>
                  <div class="text-caption text-grey">Componente</div>
                </div>
                <div class="col">
                  <div class="text-subtitle2 text-blue-7">{{ assignedHours }}h</div>
                  <div class="text-caption text-grey">Letivo</div>
                </div>
                <div class="col">
                  <div class="text-subtitle2 text-orange-7">{{ creditHours }}h</div>
                  <div class="text-caption text-grey">Crédito</div>
                </div>
              </div>
            </q-card-section>

            <q-separator />
            <q-card-section>
              <div class="text-caption text-grey-7 q-mb-xs">Horas de crédito / redução</div>
              <q-input
                v-model.number="creditHours"
                type="number"
                min="0"
                step="0.5"
                dense outlined
                placeholder="0"
                hint="Ex: apoio à direção, coordenação..."
              />
            </q-card-section>
          </template>
        </q-card>

        <!-- Year level filter -->
        <q-card flat bordered class="q-mt-sm" v-if="selectedTeacherId">
          <q-card-section>
            <div class="text-caption text-grey-7 q-mb-xs">Filtrar por ano de escolaridade</div>
            <div class="row q-gutter-xs flex-wrap">
              <q-btn
                v-for="y in allYearLevels"
                :key="y"
                dense round outline size="sm"
                :color="yearFilter.has(y) ? 'primary' : 'grey-5'"
                :label="`${y}º`"
                @click="toggleYearFilter(y)"
              />
              <q-btn
                v-if="yearFilter.size > 0"
                dense round outline size="sm"
                color="grey-5"
                icon="clear"
                title="Remover filtros"
                @click="yearFilter = new Set()"
              />
            </div>

            <!-- Quick-select by cycle -->
            <div class="row q-gutter-xs q-mt-xs">
              <q-btn dense flat size="xs" color="blue-6" label="2.º ciclo (5-6)" @click="setCycle([5, 6])" />
              <q-btn dense flat size="xs" color="deep-purple-6" label="3.º ciclo (7-9)" @click="setCycle([7, 8, 9])" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- ── Right panel: subjects by school ─────────────── -->
      <div class="col-12 col-md-9">

        <div v-if="!selectedTeacherId" class="text-center text-grey q-pa-xl">
          <q-icon name="person" size="64px" color="grey-3" />
          <div class="q-mt-sm">Selecione um professor para ver as disciplinas disponíveis</div>
        </div>

        <div v-else-if="loadingSubjects" class="text-center q-pa-xl">
          <q-spinner size="40px" color="primary" />
          <div class="q-mt-sm text-grey">A carregar disciplinas...</div>
        </div>

        <div v-else-if="groupedBySchool.length === 0" class="text-center text-grey q-pa-xl">
          <q-icon name="book_off" size="48px" color="grey-3" />
          <div class="q-mt-sm">
            Nenhuma disciplina disponível para este professor neste ano letivo.<br>
            <small>Adicione disciplinas ao professor na página <strong>Professores → Disciplinas</strong>.</small>
          </div>
        </div>

        <template v-else>
          <q-card
            v-for="school in groupedBySchool"
            :key="school.school_name"
            flat bordered
            class="q-mb-md"
          >
            <!-- School header -->
            <div class="row items-center q-px-md q-py-sm bg-primary text-white">
              <q-icon name="school" size="sm" class="q-mr-sm" />
              <span class="text-subtitle1 text-weight-medium col">{{ school.school_name }}</span>
              <span class="text-caption opacity-80">{{ school.assignedHours }}h atribuídas</span>
            </div>

            <!-- Subject groups -->
            <q-expansion-item
              v-for="subject in school.subjects"
              :key="subject.subject_name"
              default-opened
              dense
              class="subject-block"
            >
              <template #header>
                <q-item-section>
                  <div class="row items-center q-gutter-xs">
                    <span class="text-weight-medium">{{ subject.subject_name }}</span>
                    <q-badge
                      :color="subject.assignedCount > 0 ? 'positive' : 'grey-4'"
                      :text-color="subject.assignedCount > 0 ? 'white' : 'dark'"
                      :label="`${subject.assignedCount}/${filteredSubjectEntries(subject.entries).length} turmas`"
                    />
                    <q-badge
                      v-if="subject.assignedHours > 0"
                      color="blue-6"
                      text-color="white"
                      :label="`${subject.assignedHours}h`"
                    />
                  </div>
                </q-item-section>
                <!-- Assign all button -->
                <q-item-section side>
                  <q-btn
                    flat dense round size="sm"
                    icon="done_all"
                    color="positive"
                    title="Atribuir todas as turmas visíveis"
                    :loading="assigningAll === subject.subject_name"
                    @click.stop="assignAll(subject)"
                  />
                </q-item-section>
              </template>

              <q-list dense separator>
                <q-item
                  v-for="entry in filteredSubjectEntries(subject.entries)"
                  :key="entry.id"
                  clickable
                  v-ripple
                  :class="isAssigned(entry) ? 'bg-green-1' : entry.teacher_id ? 'bg-orange-1' : ''"
                  @click="toggleAssign(entry)"
                >
                  <q-item-section avatar style="min-width:36px">
                    <q-checkbox
                      :model-value="isAssigned(entry)"
                      :color="isAssigned(entry) ? 'positive' : 'grey'"
                      dense
                      @click.stop
                      @update:model-value="() => toggleAssign(entry)"
                    />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="row items-center q-gutter-xs">
                      <span>{{ entry.class_name }}</span>
                      <q-badge
                        :color="yearBadgeColor(entry.year_level)"
                        :label="`${entry.year_level}º`"
                        size="xs"
                      />
                    </q-item-label>
                    <!-- Show who is currently assigned if it's not this teacher -->
                    <q-item-label caption v-if="entry.teacher_id && !isAssigned(entry)" class="text-orange-8">
                      <q-icon name="person" size="xs" />
                      Atribuído a: {{ entry.teacher_name }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-badge
                      :color="isAssigned(entry) ? 'positive' : 'blue-2'"
                      :text-color="isAssigned(entry) ? 'white' : 'dark'"
                      :label="`${entry.hours_per_week}h`"
                    />
                  </q-item-section>
                </q-item>

                <q-item v-if="filteredSubjectEntries(subject.entries).length === 0">
                  <q-item-section class="text-grey-5 text-caption">Nenhuma turma para o ano selecionado</q-item-section>
                </q-item>
              </q-list>
            </q-expansion-item>
          </q-card>
        </template>
      </div>
    </div>
  <!-- Gerir horas dialog -->
  <q-dialog v-model="showHoursDialog" full-width>
    <q-card style="max-width:900px;width:100%">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6"><q-icon name="tune" class="q-mr-sm" color="teal-7" />Gerir horas dos docentes</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <!-- Bulk reduction toolbar -->
      <q-card-section class="q-pt-sm q-pb-none">
        <div class="row items-center q-gutter-sm">
          <q-checkbox v-model="selectAll" label="Selecionar todos" color="teal-7" @update:model-value="toggleSelectAll" />
          <q-badge v-if="selectedTeacherIds.size > 0" color="teal-7" :label="`${selectedTeacherIds.size} selecionado(s)`" />
          <q-space />
          <template v-if="selectedTeacherIds.size > 0">
            <span class="text-caption text-grey-7">Aplicar redução a selecionados:</span>
            <q-input v-model.number="bulkReduction" type="number" min="0" max="22" dense outlined style="width:80px" suffix="h" />
            <q-btn color="teal-7" dense unelevated label="Aplicar" @click="applyBulkReduction" />
          </template>
          <q-btn color="primary" unelevated label="Guardar alterações" icon="save" :loading="savingHours" @click="saveAllHours" />
        </div>
      </q-card-section>

      <q-card-section style="max-height:70vh;overflow-y:auto">
        <div v-if="hoursLoading" class="text-center q-pa-xl"><q-spinner size="40px" color="primary" /></div>
        <template v-else>
          <div class="row items-center q-mb-sm">
            <q-space />
            <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
              <template #prepend><q-icon name="search" /></template>
            </q-input>
          </div>
          <div v-for="school in hoursDialogData" :key="school.school_id" class="q-mb-lg">
            <div class="text-subtitle1 text-weight-bold text-teal-7 q-mb-sm row items-center">
              <q-icon name="school" class="q-mr-xs" />{{ school.school_name }}
              <q-badge class="q-ml-sm" color="grey-5" :label="`${school.teachers.length} docentes`" />
            </div>
            <q-table
              :rows="school.teachers"
              :columns="hoursColumns"
              row-key="id"
              flat bordered
              dense
              hide-pagination
              :rows-per-page-options="[0]"
              :filter="search"
              sort-by="name"
            >
              <template #body-cell-sel="props">
                <q-td :props="props">
                  <q-checkbox
                    :model-value="selectedTeacherIds.has(props.row.id)"
                    color="teal-7"
                    dense
                    @update:model-value="toggleTeacherSelect(props.row.id)"
                  />
                </q-td>
              </template>
              <template #body-cell-teaching_component="props">
                <q-td :props="props">
                  <q-input
                    v-model.number="props.row.teaching_component"
                    type="number" min="0" max="26" dense borderless
                    style="width:70px"
                    suffix="h"
                  />
                </q-td>
              </template>
              <template #body-cell-credit_hours="props">
                <q-td :props="props">
                  <q-input
                    v-model.number="props.row.credit_hours"
                    type="number" min="0" max="22" dense borderless
                    style="width:70px"
                    suffix="h"
                  />
                </q-td>
              </template>
              <template #body-cell-letivo="props">
                <q-td :props="props" class="text-center">
                  <q-badge
                    :color="effectiveHours(props.row) < 0 ? 'negative' : effectiveHours(props.row) === 0 ? 'positive' : 'primary'"
                    :label="`${effectiveHours(props.row)}h livres`"
                  />
                </q-td>
              </template>
            </q-table>
          </div>
        </template>
      </q-card-section>
    </q-card>
  </q-dialog>

  <!-- Component management dialog -->
  <q-dialog v-model="showComponents" persistent maximized>
    <q-card>
      <q-card-section class="row items-center q-pb-sm bg-indigo-8 text-white">
        <q-icon name="calculate" size="sm" class="q-mr-sm" />
        <div class="text-h6">Definição de Horas por Docente</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup color="white" />
      </q-card-section>

      <!-- Legend -->
      <q-card-section class="q-py-sm bg-blue-grey-1">
        <div class="row q-gutter-md items-center text-caption text-grey-8 flex-wrap">
          <span><q-icon name="school" size="xs" color="blue-7" class="q-mr-xs" /><strong>CL</strong> = Componente Letiva (22h 2.º/3.º ciclo · 25h 1.º ciclo/Pré-escolar)</span>
          <span><q-icon name="elderly" size="xs" color="indigo-6" class="q-mr-xs" /><strong>Red. Art.79°</strong> (c/ 15 anos serviço) = 50–54a → 2h · 55–59a → 4h · ≥60a → 6h</span>
          <span><q-icon name="card_membership" size="xs" color="orange-7" class="q-mr-xs" /><strong>Crédito H.</strong> = horas de crédito por cargo (reduz CL líq. — usado na elaboração do horário)</span>
          <span><q-icon name="calculate" size="xs" color="blue-7" class="q-mr-xs" /><strong>CL líq.</strong> = CL − Red.Art.79° − Crédito H.</span>
          <span><q-icon name="business" size="xs" color="teal-7" class="q-mr-xs" /><strong>TE líq.</strong> = TE_base + Red.Art.79°</span>
          <span><q-icon name="home" size="xs" color="deep-orange-7" class="q-mr-xs" /><strong>TIA</strong> = 35 − CL líq. − TE líq.</span>
        </div>
      </q-card-section>

      <q-card-section class="q-pt-sm q-pb-xs">
        <div class="row q-gutter-sm items-center flex-wrap">
          <q-btn color="blue-7" icon="school" label="CL = 22h (2.º/3.º ciclo)" unelevated dense @click="setAllBase(22)" :loading="compBulkLoading" />
          <q-btn color="teal-7" icon="school" label="CL = 25h (1.º ciclo)" unelevated dense @click="setAllBase(25)" :loading="compBulkLoading" />
          <q-btn color="indigo-6" icon="elderly" label="Aplicar Art. 79° a todos" unelevated dense @click="applyArt79All" :loading="compBulkLoading"
            :disable="compRows.every(r => !r.birth_date)" />
          <q-input v-model="compSearch" placeholder="Pesquisar professor..." dense outlined clearable style="min-width:200px">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </div>
      </q-card-section>

      <q-card-section class="q-pt-xs" style="overflow:auto;height:calc(100vh - 250px)">
        <table class="comp-table">
          <thead>
            <tr>
              <th class="comp-th comp-th--name">Professor</th>
              <th class="comp-th">Data Nasc.</th>
              <th class="comp-th comp-th--sm">Idade</th>
              <th class="comp-th comp-th--sm">CL</th>
              <th class="comp-th comp-th--sm">Red. Art.79°</th>
              <th class="comp-th comp-th--sm">CL líq.</th>
              <th class="comp-th comp-th--te">Crédito H. por Cargo</th>
              <th class="comp-th comp-th--te">Alocações TE</th>
              <th class="comp-th comp-th--sm">TE líq.</th>
              <th class="comp-th comp-th--sm">TIA</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredCompRows" :key="row.id" class="comp-row">
              <td class="comp-td comp-td--name">{{ row.name }}</td>
              <td class="comp-td">
                <div class="row no-wrap items-center" style="gap:2px">
                  <q-input v-model="row.birth_date" type="date" dense outlined style="min-width:130px"
                    @update:model-value="onBirthDateChange(row)" />
                  <q-btn v-if="row.birth_date" flat round dense size="xs" icon="close" color="grey-5"
                    @click="() => { row.birth_date = null; onBirthDateChange(row) }" />
                </div>
              </td>
              <td class="comp-td comp-td--center">
                <span v-if="row.birth_date" class="text-body2">{{ calcAge(row.birth_date) }}</span>
                <span v-else class="text-grey-5">—</span>
              </td>
              <td class="comp-td comp-td--center">
                <q-input v-model.number="row.base_teaching_hours" type="number" min="0" max="40" dense outlined
                  style="width:58px" @update:model-value="recalcTeachingComponent(row)" />
              </td>
              <td class="comp-td comp-td--center">
                <div class="row no-wrap items-center justify-center" style="gap:4px">
                  <q-input v-model.number="row.art79_reduction" type="number" min="0" max="10" dense outlined
                    style="width:54px" @update:model-value="onArt79Change(row)" />
                  <q-icon v-if="row.art79_manual" name="edit" size="xs" color="orange-6">
                    <q-tooltip>Redução manual</q-tooltip>
                  </q-icon>
                  <q-icon v-else-if="row.birth_date && row.art79_reduction > 0" name="auto_awesome" size="xs" color="indigo-4">
                    <q-tooltip>Calculado automaticamente pelo Art. 79°</q-tooltip>
                  </q-icon>
                </div>
              </td>
              <td class="comp-td comp-td--center">
                <q-badge
                  :color="clLiquida(row) < 0 ? 'negative' : 'blue-7'"
                  :label="clLiquida(row)"
                  style="font-size:13px;padding:4px 8px" />
              </td>
              <td class="comp-td comp-td--te">
                <div v-for="(alloc, i) in row.credit_role" :key="i" class="row no-wrap items-center q-mb-xs" style="gap:4px">
                  <q-select v-model="alloc.role" :options="cargoOptions" dense outlined
                    use-input input-debounce="0" clearable
                    placeholder="Cargo..." style="min-width:180px"
                    @new-value="(val, done) => done(val)" />
                  <q-input v-model.number="alloc.hours" type="number" min="1" max="20"
                    dense outlined style="width:65px" suffix="h" />
                  <q-btn flat round dense size="xs" icon="close" color="grey-5"
                    @click="removeCreditAlloc(row, i)" />
                </div>
                <div class="row items-center" style="gap:8px">
                  <q-btn flat dense size="xs" icon="add" color="orange-7" label="Adicionar"
                    @click="addCreditAlloc(row)" />
                  <span v-if="row.credit_role.length > 0" class="text-caption text-grey-7">
                    Total: <strong>{{ creditTotal(row) }}h</strong>
                  </span>
                </div>
              </td>
              <td class="comp-td comp-td--te">
                <div v-for="(alloc, i) in row.te_role" :key="i" class="row no-wrap items-center q-mb-xs" style="gap:4px">
                  <q-select v-model="alloc.role" :options="teAllocOptions" dense outlined
                    use-input input-debounce="0" clearable
                    placeholder="Cargo / Atividade..." style="min-width:180px"
                    @new-value="(val, done) => done(val)" />
                  <q-input v-model.number="alloc.hours" type="number" min="1" max="20"
                    dense outlined style="width:65px" suffix="h" />
                  <q-btn flat round dense size="xs" icon="close" color="grey-5"
                    @click="removeTeAlloc(row, i)" />
                </div>
                <div class="row items-center" style="gap:8px">
                  <q-btn flat dense size="xs" icon="add" color="teal-7" label="Adicionar"
                    @click="addTeAlloc(row)" />
                  <span v-if="row.te_role.length > 0" class="text-caption text-grey-7">
                    Total: <strong>{{ row.te_role.reduce((s,a) => s + (Number(a.hours)||0), 0) }}h</strong>
                  </span>
                </div>
              </td>
              <td class="comp-td comp-td--center">
                <q-badge color="teal-7"
                  :label="teLiquido(row)"
                  style="font-size:13px;padding:4px 8px" />
              </td>
              <td class="comp-td comp-td--center">
                <q-badge color="deep-orange-7"
                  :label="tia(row)"
                  style="font-size:13px;padding:4px 8px" />
              </td>
            </tr>
          </tbody>
        </table>
      </q-card-section>

      <q-card-actions align="right" class="q-px-md q-pb-md q-gutter-sm">
        <q-btn flat label="Cancelar" v-close-popup />
        <q-btn color="indigo-7" icon="save" label="Guardar tudo" :loading="compBulkLoading" @click="saveComponents" />
      </q-card-actions>
    </q-card>
  </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useClustersStore } from 'stores/clusters'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useTeachersStore } from 'stores/teachers'

const $q = useQuasar()
const clustersStore = useClustersStore()
const yearsStore = useAcademicYearsStore()
const teachersStore = useTeachersStore()

type Entry = {
  id: number
  class_id: number
  class_name: string
  year_level: number
  school_id: number | null
  school_name: string
  subject_id: number
  subject_name: string
  hours_per_week: number
  teacher_id: number | null
  teacher_name: string | null
}

// ── State ──────────────────────────────────────────────
const search = ref('')
const selectedYearId = ref<number | null>(null)
const selectedTeacherId = ref<number | null>(null)
const allEntries = ref<Entry[]>([])
const teacherSubjectIds = ref<number[]>([])
const creditHours = ref(0)
const yearFilter = ref<Set<number>>(new Set())
const loadingSubjects = ref(false)
const teacherFilterText = ref('')
const assigningAll = ref<string | null>(null)

// ── Computed ───────────────────────────────────────────
const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)

const yearOptions = computed(() =>
  yearsStore.years.map((y) => ({ label: y.name, value: y.id }))
)

const selectedTeacher = computed(() =>
  teachersStore.teachers.find((t) => t.id === selectedTeacherId.value) ?? null
)

const filteredTeacherOptions = ref(
  teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
)

function filterTeachersFn(val: string, update: (fn: () => void) => void) {
  update(() => {
    teacherFilterText.value = val
    const txt = val.toLowerCase()
    filteredTeacherOptions.value = teachersStore.teachers
      .filter((t) => t.name.toLowerCase().includes(txt))
      .map((t) => ({ label: t.name, value: t.id }))
  })
}

const assignedHours = computed(() => {
  if (!selectedTeacherId.value) return 0
  return allEntries.value
    .filter((e) => e.teacher_id === selectedTeacherId.value)
    .reduce((sum, e) => sum + e.hours_per_week, 0)
})

const totalHours = computed(() => selectedTeacher.value?.teaching_component ?? 0)
const usedHours = computed(() => assignedHours.value + creditHours.value)
const remainingHours = computed(() => totalHours.value - usedHours.value)

const progressRatio = computed(() =>
  totalHours.value > 0 ? Math.min(1, usedHours.value / totalHours.value) : 0
)

const progressColor = computed(() => {
  if (remainingHours.value < 0) return 'negative'
  if (remainingHours.value === 0) return 'positive'
  if (progressRatio.value > 0.85) return 'warning'
  return 'primary'
})

const allYearLevels = computed(() => {
  const years = new Set(allEntries.value.map((e) => e.year_level))
  return [...years].sort((a, b) => a - b)
})

// Entries for teacher's subjects, grouped by school → subject
const groupedBySchool = computed(() => {
  if (!selectedTeacherId.value || teacherSubjectIds.value.length === 0) return []

  const relevant = allEntries.value.filter((e) =>
    teacherSubjectIds.value.includes(e.subject_id)
  )

  const schoolMap = new Map<string, Map<string, Entry[]>>()
  for (const entry of relevant) {
    const sn = entry.school_name || entry.class_name.split(' ').pop() || 'Outras'
    if (!schoolMap.has(sn)) schoolMap.set(sn, new Map())
    const subjMap = schoolMap.get(sn)!
    if (!subjMap.has(entry.subject_name)) subjMap.set(entry.subject_name, [])
    subjMap.get(entry.subject_name)!.push(entry)
  }

  return [...schoolMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([school_name, subjMap]) => {
      const subjects = [...subjMap.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([subject_name, entries]) => {
          const sorted = [...entries].sort(
            (a, b) => a.year_level - b.year_level || a.class_name.localeCompare(b.class_name)
          )
          const assignedEntries = sorted.filter((e) => e.teacher_id === selectedTeacherId.value)
          return {
            subject_name,
            entries: sorted,
            assignedCount: assignedEntries.length,
            assignedHours: assignedEntries.reduce((s, e) => s + e.hours_per_week, 0),
          }
        })
      const schoolAssignedHours = subjects.reduce((s, sub) => s + sub.assignedHours, 0)
      return { school_name, subjects, assignedHours: schoolAssignedHours }
    })
})

// ── Helpers ────────────────────────────────────────────
function filteredSubjectEntries(entries: Entry[]) {
  if (yearFilter.value.size === 0) return entries
  return entries.filter((e) => yearFilter.value.has(e.year_level))
}

function isAssigned(entry: Entry) {
  return entry.teacher_id === selectedTeacherId.value
}

function toggleYearFilter(y: number) {
  const s = new Set(yearFilter.value)
  s.has(y) ? s.delete(y) : s.add(y)
  yearFilter.value = s
}

function setCycle(years: number[]) {
  yearFilter.value = new Set(years)
}

const yearColors = ['blue', 'teal', 'green', 'orange', 'purple', 'red', 'pink', 'brown', 'cyan']
function yearBadgeColor(y: number) {
  return yearColors[(y - 1) % yearColors.length] ?? 'grey'
}

// ── Actions ────────────────────────────────────────────
async function onYearChange() {
  allEntries.value = []
  selectedTeacherId.value = null
  teacherSubjectIds.value = []
  creditHours.value = 0
  yearFilter.value = new Set()
  if (!selectedYearId.value || !clusterId.value) return

  await Promise.all([
    clustersStore.fetchAll(),
    yearsStore.fetchAll(),
    teachersStore.fetchAll(),
  ])

  const { data } = await api.get<Entry[]>('/classes/curriculum-overview', {
    params: { cluster_id: clusterId.value, academic_year_id: selectedYearId.value },
  })
  allEntries.value = data

  // Reset teacher filter options
  filteredTeacherOptions.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
}

async function onTeacherChange() {
  teacherSubjectIds.value = []
  yearFilter.value = new Set()
  if (!selectedTeacherId.value) return
  // Pre-populate credit hours from stored value
  const t = teachersStore.teachers.find((t) => t.id === selectedTeacherId.value)
  creditHours.value = t?.credit_hours ?? 0
  loadingSubjects.value = true
  try {
    const { data } = await api.get(`/teachers/${selectedTeacherId.value}/subjects`)
    teacherSubjectIds.value = (data as { subject_id: number }[]).map((ts) => ts.subject_id)
  } finally {
    loadingSubjects.value = false
  }
}

async function toggleAssign(entry: Entry) {
  if (!selectedTeacherId.value) return
  const newTeacherId = isAssigned(entry) ? null : selectedTeacherId.value
  try {
    await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: newTeacherId })
    entry.teacher_id = newTeacherId
    entry.teacher_name = newTeacherId
      ? (teachersStore.teachers.find((t) => t.id === newTeacherId)?.name ?? null)
      : null
    $q.notify({
      type: newTeacherId ? 'positive' : 'info',
      message: newTeacherId ? `+${entry.hours_per_week}h — ${entry.class_name}` : `−${entry.hours_per_week}h — ${entry.class_name}`,
      timeout: 1000,
    })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar atribuição' })
  }
}

async function assignAll(subject: { subject_name: string; entries: Entry[] }) {
  if (!selectedTeacherId.value) return
  const toAssign = filteredSubjectEntries(subject.entries).filter(
    (e) => !isAssigned(e) && !e.teacher_id
  )
  if (toAssign.length === 0) return
  assigningAll.value = subject.subject_name
  for (const entry of toAssign) {
    await toggleAssign(entry)
  }
  assigningAll.value = null
}

// ── Gerir horas dialog ─────────────────────────────────
type HoursRow = { id: number; name: string; teaching_component: number; credit_hours: number; assigned_hours: number }
type HoursSchool = { school_id: number; school_name: string; teachers: HoursRow[] }

const showHoursDialog = ref(false)
const hoursLoading = ref(false)
const savingHours = ref(false)
const hoursDialogData = ref<HoursSchool[]>([])
const selectedTeacherIds = ref<Set<number>>(new Set())
const selectAll = ref(false)
const bulkReduction = ref(0)

const hoursColumns = [
  { name: 'sel', label: '', field: 'sel', align: 'center' as const, style: 'width:40px' },
  { name: 'name', label: 'Professor', field: 'name', align: 'left' as const },
  { name: 'teaching_component', label: 'Componente (h)', field: 'teaching_component', align: 'center' as const },
  { name: 'credit_hours', label: 'Redução (h)', field: 'credit_hours', align: 'center' as const },
  { name: 'letivo', label: 'Saldo', field: 'letivo', align: 'center' as const },
]

function effectiveHours(row: HoursRow) {
  return (row.teaching_component ?? 0) - (row.credit_hours ?? 0) - (row.assigned_hours ?? 0)
}

async function openHoursDialog() {
  showHoursDialog.value = true
  hoursLoading.value = true
  selectedTeacherIds.value = new Set()
  selectAll.value = false
  try {
    const teachers = teachersStore.teachers
    // Compute assigned hours per teacher from allEntries
    const assignedMap = new Map<number, number>()
    for (const e of allEntries.value) {
      if (e.teacher_id) assignedMap.set(e.teacher_id, (assignedMap.get(e.teacher_id) ?? 0) + e.hours_per_week)
    }
    // Group by school via school_ids
    const schoolMap = new Map<number, { name: string; teachers: HoursRow[] }>()
    // Get schools from store
    const { useSchoolsStore } = await import('stores/schools')
    const schoolsStore = useSchoolsStore()
    if (!schoolsStore.schools.length) await schoolsStore.fetchAll()
    const schoolNames = new Map(schoolsStore.schools.map((s) => [s.id, s.name]))

    for (const t of teachers) {
      const schoolIds = t.school_ids?.length ? t.school_ids : [0]
      for (const sid of schoolIds) {
        if (!schoolMap.has(sid)) schoolMap.set(sid, { name: schoolNames.get(sid) ?? 'Sem escola', teachers: [] })
        // Only add once (first school)
        if (sid === schoolIds[0]) {
          schoolMap.get(sid)!.teachers.push({
            id: t.id,
            name: t.name,
            teaching_component: t.teaching_component ?? 22,
            credit_hours: t.credit_hours ?? 0,
            assigned_hours: assignedMap.get(t.id) ?? 0,
          })
        }
      }
    }
    hoursDialogData.value = [...schoolMap.entries()]
      .sort(([, a], [, b]) => a.name.localeCompare(b.name))
      .map(([school_id, v]) => ({ school_id, school_name: v.name, teachers: v.teachers.sort((a, b) => a.name.localeCompare(b.name)) }))
  } finally {
    hoursLoading.value = false
  }
}

function toggleTeacherSelect(id: number) {
  const s = new Set(selectedTeacherIds.value)
  s.has(id) ? s.delete(id) : s.add(id)
  selectedTeacherIds.value = s
}

function toggleSelectAll(val: boolean) {
  if (val) {
    const all = new Set<number>()
    for (const school of hoursDialogData.value) school.teachers.forEach((t) => all.add(t.id))
    selectedTeacherIds.value = all
  } else {
    selectedTeacherIds.value = new Set()
  }
}

function applyBulkReduction() {
  for (const school of hoursDialogData.value) {
    for (const t of school.teachers) {
      if (selectedTeacherIds.value.has(t.id)) t.credit_hours = bulkReduction.value
    }
  }
  $q.notify({ type: 'positive', message: `Redução de ${bulkReduction.value}h aplicada a ${selectedTeacherIds.value.size} docente(s)` })
}

async function saveAllHours() {
  savingHours.value = true
  try {
    const payload = hoursDialogData.value.flatMap((s) =>
      s.teachers.map((t) => ({ id: t.id, teaching_component: t.teaching_component, credit_hours: t.credit_hours }))
    )
    await api.put('/teachers/bulk-update', payload)
    await teachersStore.fetchAll()
    $q.notify({ type: 'positive', message: 'Horas guardadas com sucesso' })
    showHoursDialog.value = false
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar' })
  } finally {
    savingHours.value = false
  }
}

// ── Componentes dialog ─────────────────────────────────
interface TeAllocation { role: string; hours: number }
interface CreditAllocation { role: string; hours: number }

interface CompRow {
  id: number
  name: string
  birth_date: string | null
  base_teaching_hours: number  // CL — Componente Letiva
  te_role: TeAllocation[]      // alocações TE com horas por atividade
  credit_role: CreditAllocation[]  // crédito horário com horas por cargo
  art79_reduction: number
  art79_manual: boolean
  teaching_component: number   // = CL líquida = CL - art79 - crédito
}

const showComponents = ref(false)
const compRows = ref<CompRow[]>([])
const compSearch = ref('')
const compBulkLoading = ref(false)

const cargoOptions = [
  'Diretor de Turma',
  'Coordenador de Departamento',
  'Coordenador dos Diretores de Turma',
  'Assessor de Direção',
  'Representante de Grupo Disciplinar',
  'Coordenador de Projetos',
  'Dinamizador de Biblioteca / CRE',
  'Coordenador de Ano',
  'Orientador de Estágio',
  'Direção',
]

const teAllocOptions = [
  ...cargoOptions,
  'Reuniões de avaliação',
  'Trabalho de coordenação pedagógica',
  'Apoio educativo',
  'Atendimento a encarregados de educação',
  'Reuniões de departamento / grupo',
  'Reuniões de conselho de turma',
  'Atividades de complemento curricular',
]

const filteredCompRows = computed(() => {
  if (!compSearch.value) return compRows.value
  const q = compSearch.value.toLowerCase()
  return compRows.value.filter((r) => r.name.toLowerCase().includes(q))
})

function calcAge(birthDateStr: string): number {
  const today = new Date()
  const bd = new Date(birthDateStr)
  let age = today.getFullYear() - bd.getFullYear()
  if (today.getMonth() < bd.getMonth() || (today.getMonth() === bd.getMonth() && today.getDate() < bd.getDate())) age--
  return age
}

function calcArt79(birthDateStr: string): number {
  const age = calcAge(birthDateStr)
  if (age >= 60) return 6
  if (age >= 55) return 4
  if (age >= 50) return 2
  return 0
}

function creditTotal(row: CompRow): number {
  return row.credit_role.reduce((s, a) => s + (Number(a.hours) || 0), 0)
}

function clLiquida(row: CompRow): number {
  return Math.max(0, row.base_teaching_hours - row.art79_reduction - creditTotal(row))
}

function teLiquido(row: CompRow): number {
  const teBase = row.te_role.reduce((s, a) => s + (Number(a.hours) || 0), 0)
  return Math.max(0, teBase + row.art79_reduction)
}

function tia(row: CompRow): number {
  return Math.max(0, 35 - clLiquida(row) - teLiquido(row))
}

function addTeAlloc(row: CompRow) {
  row.te_role.push({ role: '', hours: 1 })
}

function removeTeAlloc(row: CompRow, i: number) {
  row.te_role.splice(i, 1)
}

function addCreditAlloc(row: CompRow) {
  row.credit_role.push({ role: '', hours: 1 })
}

function removeCreditAlloc(row: CompRow, i: number) {
  row.credit_role.splice(i, 1)
}

function recalcTeachingComponent(row: CompRow) {
  row.teaching_component = clLiquida(row)
}

function onBirthDateChange(row: CompRow) {
  if (!row.art79_manual) {
    row.art79_reduction = row.birth_date ? calcArt79(row.birth_date) : 0
  }
  recalcTeachingComponent(row)
}

function onArt79Change(row: CompRow) {
  row.art79_manual = true
  recalcTeachingComponent(row)
}

async function openComponentDialog() {
  if (!clusterId.value) return
  compBulkLoading.value = true
  compSearch.value = ''
  try {
    const { data } = await api.get('/teachers', { params: { cluster_id: clusterId.value } })
    type ApiTeacher = {
      id: number; name: string; birth_date: string | null
      teaching_component: number | null; credit_hours: number | null; credit_role: string | null
      base_teaching_hours: number | null; te_hours: number | null; te_role: string | null
    }
    compRows.value = (data as ApiTeacher[]).map(t => {
      const base_teaching_hours = t.base_teaching_hours ?? 22
      const art79Auto = t.birth_date ? calcArt79(t.birth_date) : 0
      const art79_reduction = art79Auto
      const art79_manual = false
      let te_role: TeAllocation[] = []
      if (t.te_role) {
        try {
          const parsed = JSON.parse(t.te_role)
          if (Array.isArray(parsed)) {
            te_role = parsed.length > 0 && typeof parsed[0] === 'string'
              ? parsed.map((s: string) => ({ role: s, hours: 1 }))
              : parsed as TeAllocation[]
          }
        } catch { te_role = [] }
      }
      if (te_role.length === 0) {
        te_role = [{ role: 'Reuniões e trabalho de estabelecimento', hours: t.te_hours ?? 3 }]
      }
      let credit_role: CreditAllocation[] = []
      if (t.credit_role) {
        try {
          const parsed = JSON.parse(t.credit_role)
          if (Array.isArray(parsed)) {
            credit_role = parsed.length > 0 && typeof parsed[0] === 'string'
              ? [{ role: parsed[0], hours: t.credit_hours ?? 1 }]
              : parsed as CreditAllocation[]
          } else {
            credit_role = [{ role: t.credit_role, hours: t.credit_hours ?? 1 }]
          }
        } catch {
          credit_role = [{ role: t.credit_role, hours: t.credit_hours ?? 1 }]
        }
      } else if (t.credit_hours && t.credit_hours > 0) {
        credit_role = [{ role: '', hours: t.credit_hours }]
      }
      const teaching_component = Math.max(0, base_teaching_hours - art79_reduction - credit_role.reduce((s, a) => s + (a.hours || 0), 0))
      return {
        id: t.id, name: t.name, birth_date: t.birth_date ?? null,
        base_teaching_hours, te_role, credit_role,
        art79_reduction, art79_manual, teaching_component,
      }
    }).sort((a, b) => a.name.localeCompare(b.name))
  } finally {
    compBulkLoading.value = false
  }
  showComponents.value = true
}

function setAllBase(base: number) {
  compRows.value.forEach(r => { r.base_teaching_hours = base; recalcTeachingComponent(r) })
}

function applyArt79All() {
  compRows.value.forEach(r => {
    if (r.birth_date) { r.art79_reduction = calcArt79(r.birth_date); r.art79_manual = false; recalcTeachingComponent(r) }
  })
}

async function saveComponents() {
  compBulkLoading.value = true
  try {
    const payload = compRows.value.map(r => ({
      id: r.id, teaching_component: clLiquida(r), birth_date: r.birth_date || null,
      base_teaching_hours: r.base_teaching_hours,
      te_hours: r.te_role.reduce((s, a) => s + (a.hours || 0), 0),
      te_role: r.te_role.length ? JSON.stringify(r.te_role) : null,
      credit_hours: creditTotal(r),
      credit_role: r.credit_role.length ? JSON.stringify(r.credit_role) : null,
    }))
    await api.put('/teachers/bulk-update', payload)
    await teachersStore.fetchAll()
    $q.notify({ type: 'positive', message: `${payload.length} professor(es) atualizados` })
    showComponents.value = false
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar — tente novamente' })
  } finally {
    compBulkLoading.value = false
  }
}

// Initialize
import { onMounted } from 'vue'
onMounted(async () => {
  await Promise.all([clustersStore.fetchAll(), yearsStore.fetchAll(), teachersStore.fetchAll()])
  filteredTeacherOptions.value = teachersStore.teachers.map((t) => ({ label: t.name, value: t.id }))
  selectedYearId.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  if (selectedYearId.value) await onYearChange()
})
</script>

<style scoped>
.subject-block {
  border-top: 1px solid rgba(0,0,0,0.08);
}
.body--dark .subject-block {
  border-top-color: rgba(255,255,255,0.08);
}
.comp-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
}
.comp-th {
  padding: 6px 8px;
  border: 1px solid #ccc;
  background: #2c3e50;
  color: white;
  text-align: center;
  white-space: nowrap;
  position: sticky;
  top: 0;
  z-index: 2;
}
.comp-th--name { text-align: left; min-width: 160px; }
.comp-th--sm { min-width: 70px; }
.comp-th--cargo { min-width: 200px; text-align: left; }
.comp-th--te { min-width: 300px; text-align: left; }
.comp-td--te { vertical-align: top; padding-top: 6px; }
.comp-td {
  padding: 3px 6px;
  border: 1px solid #e0e0e0;
  vertical-align: middle;
}
.comp-td--name { font-weight: 500; white-space: nowrap; }
.comp-td--center { text-align: center; }
.comp-row:hover { background: rgba(0,0,0,0.03); }
.body--dark .comp-th { background: #1a2332; }
.body--dark .comp-td { border-color: #444; }
.body--dark .comp-row:hover { background: rgba(255,255,255,0.05); }
</style>
