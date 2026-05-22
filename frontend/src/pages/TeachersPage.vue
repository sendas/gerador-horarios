<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">Professores</div>
      <q-space />
      <q-input v-model="search" placeholder="Pesquisar..." dense outlined clearable style="min-width:200px">
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn color="orange-7" icon="event_busy" label="Blocos indisponíveis" @click="openBulkAvail" class="q-ml-sm">
        <q-tooltip>Definir blocos indisponíveis para todos os professores do agrupamento</q-tooltip>
      </q-btn>
      <q-btn color="primary" icon="add" label="Novo" @click="openCreate" class="q-ml-sm" />
      <q-btn color="secondary" icon="upload" label="Importar" @click="showImport = true" class="q-ml-sm" />
    </div>

    <ImportDialog
      v-model="showImport"
      title="Importar Professores"
      endpoint="/imports/teachers"
      :extra-params="{ cluster_id: selectedClusterId }"
      entity-type="teachers"
      @done="teachersStore.fetchAll()"
    />

    <!-- School filter -->
    <div class="row items-center q-mb-sm q-gutter-xs">
      <span class="text-caption text-grey-7 q-mr-xs">Filtrar por escola:</span>
      <q-chip
        v-for="school in schoolsStore.schools"
        :key="school.id"
        clickable
        :color="selectedSchoolIds.has(school.id) ? 'teal-7' : 'grey-3'"
        :text-color="selectedSchoolIds.has(school.id) ? 'white' : 'dark'"
        :icon="selectedSchoolIds.has(school.id) ? 'check' : undefined"
        :label="school.name"
        @click="toggleSchoolFilter(school.id)"
      />
      <q-btn v-if="selectedSchoolIds.size > 0" flat dense size="sm" icon="close" color="grey-6" label="Limpar" @click="selectedSchoolIds.clear()" />
      <q-badge v-if="selectedSchoolIds.size > 0" color="teal-7" :label="`${filteredTeachers.length} professor(es)`" class="q-ml-xs" />
    </div>

    <q-table :rows="filteredTeachers" :columns="columns" row-key="id" :loading="teachersStore.loading" :filter="search" sort-by="name">
      <template #body="props">
        <q-tr :props="props">
          <q-td key="name" :props="props" class="cursor-pointer" style="white-space:nowrap" @click="toggleTeacherExpand(props.row)">
            <q-icon :name="expandedTeacherId === props.row.id ? 'expand_less' : 'expand_more'" size="xs" color="grey-6" class="q-mr-xs" />
            {{ props.row.name }}
          </q-td>
          <q-td key="primary_school" :props="props">
            <span v-if="props.row.primary_school_name">
              <q-icon name="star" color="amber-7" size="xs" class="q-mr-xs" />{{ props.row.primary_school_name }}
            </span>
            <span v-else-if="props.row.school_ids?.length" class="text-caption text-grey-6">
              {{ props.row.school_ids.length }} escola(s) — sem base
            </span>
            <span v-else class="text-caption text-orange-7">
              <q-icon name="warning" size="xs" /> sem escola
            </span>
          </q-td>
          <q-td key="subject_names" :props="props">
            <q-chip v-for="s in props.row.subject_names" :key="s" size="sm" :label="s" color="blue-2" text-color="dark" class="q-mr-xs" />
            <span v-if="!props.row.subject_names?.length" class="text-grey-5">—</span>
          </q-td>
          <q-td key="teaching_component" :props="props" class="text-center">{{ props.row.teaching_component ?? '—' }}</q-td>
          <q-td key="max_daily_lessons" :props="props" class="text-center">{{ props.row.max_daily_lessons ?? '—' }}</q-td>
          <q-td key="preferred_free_day" :props="props" class="text-center">
            {{ props.row.preferred_free_day !== null && props.row.preferred_free_day !== undefined ? DAYS[props.row.preferred_free_day] : '—' }}
          </q-td>
          <q-td key="actions" :props="props">
            <q-btn unelevated size="sm" color="info" icon="school" label="Escolas" @click="openSchools(props.row)" class="q-mr-xs" />
            <q-btn unelevated size="sm" color="secondary" icon="book" label="Disciplinas" @click="openSubjects(props.row)" class="q-mr-xs" />
            <q-btn unelevated size="sm" color="teal" icon="groups" label="Turmas" @click="openCurriculum(props.row)" class="q-mr-xs" />
            <q-btn unelevated size="sm" color="positive" icon="event_available" label="Disponibilidade" @click="openAvailability(props.row)" class="q-mr-xs" />
            <q-btn unelevated size="sm" color="grey-6" icon="edit" label="Editar" @click="openEdit(props.row)" class="q-mr-xs" />
            <q-btn unelevated size="sm" color="negative" icon="delete" label="Apagar" @click="confirmDelete(props.row)" />
          </q-td>
        </q-tr>
        <q-tr v-show="expandedTeacherId === props.row.id" :props="props">
          <q-td :colspan="columns.length" class="q-pa-sm bg-blue-grey-1">
            <div v-if="expandLoading" class="text-grey-6 text-caption q-pa-xs">A carregar...</div>
            <div v-else class="row q-gutter-md items-start q-pl-sm">
              <div>
                <div class="text-caption text-grey-7 q-mb-xs">Escolas</div>
                <template v-if="props.row.school_ids?.length">
                  <q-chip
                    v-for="sid in props.row.school_ids"
                    :key="sid"
                    dense
                    :icon="sid === props.row.primary_school_id ? 'star' : 'school'"
                    :color="sid === props.row.primary_school_id ? 'amber-7' : 'blue-grey-3'"
                    :text-color="sid === props.row.primary_school_id ? 'white' : 'dark'"
                    :label="schoolName(sid)"
                  />
                </template>
                <span v-else class="text-caption text-grey-5">sem escola</span>
              </div>
              <q-separator vertical />
              <div>
                <div class="text-caption text-grey-7 q-mb-xs">Turmas atribuídas</div>
                <template v-if="expandedTeacherId === props.row.id && expandedClasses.length">
                  <q-chip
                    v-for="cls in expandedClasses"
                    :key="cls.class_id"
                    dense
                    color="teal-2"
                    text-color="dark"
                    :label="`${cls.class_name} (${cls.year_level}º)`"
                  />
                </template>
                <span v-else-if="expandedTeacherId === props.row.id" class="text-caption text-grey-5">sem turmas atribuídas</span>
              </div>
            </div>
          </q-td>
        </q-tr>
      </template>
    </q-table>

    <!-- Bulk availability grid dialog -->
    <q-dialog v-model="bulkAvailDialog" persistent full-width>
      <q-card style="max-width:900px;width:100%">
        <q-card-section class="bg-orange-7 text-white row items-center">
          <div>
            <div class="text-h6">Blocos indisponíveis — todos os professores</div>
            <div class="text-caption">Clique nos blocos para os marcar como indisponíveis (vermelho). Aplica a todos os docentes do agrupamento.</div>
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <div class="row items-center q-gutter-sm q-mb-md">
            <q-select
              v-model="bulkAvailYear"
              :options="yearOptions"
              label="Ano letivo"
              emit-value map-options dense outlined
              style="min-width:180px"
              @update:model-value="() => { clearBulkSlots(); loadBulkSlots() }"
            />
            <q-chip v-if="bulkBlockedCount > 0" color="negative" text-color="white" icon="block" :label="`${bulkBlockedCount} bloco(s) bloqueado(s)`" />
            <q-btn v-if="bulkBlockedCount > 0" flat dense size="sm" icon="clear" label="Limpar tudo" color="grey-6" @click="clearBulkSlots()" />
          </div>

          <div v-if="bulkAvailLoading" class="text-center q-py-lg text-grey-6">A carregar tempos letivos...</div>
          <div v-else-if="bulkAvailYear && bulkUniqueSlots.length === 0" class="text-center q-py-lg text-grey-6">
            Nenhum tempo letivo configurado para este ano.
          </div>
          <div v-else-if="bulkAvailYear" class="bulk-avail-grid-wrap">
            <table class="bulk-avail-table">
              <thead>
                <tr>
                  <th class="bulk-avail-th bulk-avail-th--slot">Tempo</th>
                  <th v-for="(day, di) in DAYS" :key="di" class="bulk-avail-th">{{ day }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="slot in bulkUniqueSlots" :key="slot.slot_number">
                  <td class="bulk-avail-td bulk-avail-td--label">
                    <span class="text-weight-bold">{{ slot.slot_number }}</span>
                    <span class="text-caption text-grey-6 q-ml-xs">{{ slot.start_time }}–{{ slot.end_time }}</span>
                  </td>
                  <td
                    v-for="(day, di) in DAYS" :key="di"
                    class="bulk-avail-td bulk-avail-td--cell"
                    :class="{ 'bulk-avail-td--blocked': isBulkBlocked(di, slot.slot_number) }"
                    @click="toggleBulkSlot(di, slot.slot_number)"
                  >
                    <q-icon v-if="isBulkBlocked(di, slot.slot_number)" name="block" size="sm" color="white" />
                    <q-icon v-else name="check" size="sm" color="positive" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-center text-grey-6 q-py-lg">Selecione um ano letivo.</div>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md q-gutter-sm">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn
            label="Aplicar a todos"
            color="orange-7"
            icon="save"
            :loading="bulkAvailSaving"
            :disable="!bulkAvailYear"
            @click="applyBulkAvail"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Teacher dialog -->
    <q-dialog v-model="dialog">
      <q-card style="min-width: 450px">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ editing ? 'Editar' : 'Novo' }} Professor</div>
          <q-space /><q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-form @submit.prevent="save" greedy>
            <q-select v-if="!editing" v-model="form.cluster_id" :options="clusterOptions" label="Agrupamento *" emit-value map-options :rules="[v => !!v || 'Obrigatório']" class="q-mb-sm" />
            <q-input v-model="form.name" label="Nome *" :rules="[v => !!v || 'Obrigatório']" class="q-mb-sm" />
            <q-input v-model="form.email" label="Email" type="email" />
            <q-input v-model.number="form.max_daily_lessons" label="Máx aulas/dia" type="number" min="1" max="10" />
            <q-select
              v-model="form.preferred_free_day"
              :options="dayOptions"
              label="Dia livre preferido"
              emit-value map-options clearable
            />
            <q-separator class="q-my-sm" />
            <div class="text-caption text-grey-6 q-mb-sm">Preferências de horário</div>

            <div class="row q-gutter-sm">
              <q-input
                v-model.number="form.min_start_slot"
                label="Não entrar antes do tempo n.°"
                type="number"
                min="1"
                :max="10"
                hint="Ex: 2 = não começa no 1.° tempo"
                style="min-width: 200px"
                clearable
              />
              <q-input
                v-model.number="form.max_end_slot"
                label="Não sair depois do tempo n.°"
                type="number"
                min="1"
                :max="10"
                hint="Ex: 6 = termina no máximo no 6.° tempo"
                style="min-width: 200px"
                clearable
              />
            </div>
            <q-select
              v-model="form.preferred_shift"
              :options="shiftOptions"
              label="Turno preferido"
              emit-value
              map-options
              clearable
            />
            <q-input
              v-model.number="form.max_consecutive_lessons"
              label="Máx. aulas consecutivas (sobrepõe-se à regra global)"
              type="number"
              min="1"
              :max="8"
              clearable
              hint="Deixa vazio para usar a regra global"
            />
            <q-separator class="q-my-sm" />
            <div class="text-caption text-grey-6 q-mb-sm">Componente letiva</div>
            <q-input
              v-model.number="form.teaching_component"
              label="Horas letivas/semana"
              type="number"
              min="14"
              max="22"
              clearable
              hint="Entre 14 e 22 horas letivas por semana"
            />
            <div class="row justify-end q-mt-md q-gutter-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" color="primary" :label="editing ? 'Guardar' : 'Criar'" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Schools dialog -->
    <q-dialog v-model="schoolsDialog">
      <q-card style="min-width: 520px">
        <q-card-section class="row items-center">
          <div class="text-h6">Escolas: {{ selectedTeacher?.name }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-banner v-if="!schoolAssignments.length" class="bg-orange-1 text-orange-9" rounded dense>
            <template #avatar><q-icon name="warning" /></template>
            Sem escola atribuída — este professor pode ser alocado a qualquer escola.
            Adicione pelo menos a escola base para restringir a atribuição.
          </q-banner>
          <q-list v-else bordered separator class="rounded-borders">
            <q-item v-for="a in schoolAssignments" :key="a.id">
              <q-item-section avatar>
                <q-btn
                  flat round
                  :icon="a.is_primary ? 'star' : 'star_border'"
                  :color="a.is_primary ? 'amber-7' : 'grey-5'"
                  size="sm"
                  @click="setPrimarySchool(a.id)"
                >
                  <q-tooltip>{{ a.is_primary ? 'Escola base (principal)' : 'Definir como escola base' }}</q-tooltip>
                </q-btn>
              </q-item-section>
              <q-item-section>
                <q-item-label>
                  {{ a.school_name || schoolName(a.school_id) }}
                  <q-badge v-if="a.is_primary" color="amber-7" label="Principal" class="q-ml-xs" />
                </q-item-label>
                <q-item-label caption>{{ yearName(a.academic_year_id) }} · {{ a.travel_time_minutes }} min viagem</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn flat round icon="delete" size="sm" color="negative" @click="removeSchoolAssignment(a.id)" />
              </q-item-section>
            </q-item>
          </q-list>
          <q-separator class="q-my-md" />
          <div class="text-subtitle2 q-mb-sm">Adicionar escola</div>
          <div class="row q-col-gutter-sm items-end">
            <div class="col-4">
              <q-select v-model="newAssignment.school_id" :options="schoolOptions" label="Escola" emit-value map-options dense />
            </div>
            <div class="col-3">
              <q-select v-model="newAssignment.academic_year_id" :options="yearOptions" label="Ano Letivo" emit-value map-options dense />
            </div>
            <div class="col-2">
              <q-input v-model.number="newAssignment.travel_time_minutes" label="Viagem (min)" type="number" dense />
            </div>
            <div class="col-auto">
              <q-toggle v-model="newAssignment.is_primary" label="Principal" color="amber-7" dense />
            </div>
            <div class="col-auto">
              <q-btn round color="primary" icon="add" dense @click="addSchoolAssignment" />
            </div>
          </div>
          <div class="text-caption text-grey-6 q-mt-xs">
            <q-icon name="info" size="xs" /> Professores sem escola atribuída podem ser colocados em qualquer escola.
            Professores com escolas definidas só serão alocados nessas escolas.
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Subjects dialog -->
    <q-dialog v-model="subjectsDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="row items-center">
          <div class="text-h6">Disciplinas: {{ selectedTeacher?.name }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-xs q-mb-md">
            <q-chip
              v-for="s in teacherSubjects"
              :key="s.subject_id"
              removable
              @remove="removeSubject(s.subject_id)"
              :label="subjectName(s.subject_id)"
              color="primary"
              text-color="white"
            />
          </div>
          <div class="row q-col-gutter-sm items-center">
            <div class="col">
              <q-select v-model="newSubjectId" :options="availableSubjectOptions" label="Adicionar disciplina" emit-value map-options dense />
            </div>
            <div>
              <q-btn round color="primary" icon="add" @click="addSubject" :disable="!newSubjectId" />
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Curriculum / class assignment dialog -->
    <q-dialog v-model="curriculumDialog" full-width>
      <q-card style="max-width:960px;width:100%">
        <q-card-section class="row items-center q-pb-sm">
          <div class="text-h6 row items-center q-gutter-sm">
            <span>
              <q-icon name="groups" color="teal" class="q-mr-xs" />
              Turmas de {{ selectedTeacher?.name }}
            </span>
            <q-chip
              v-if="teachingComponent"
              dense square
              :color="assignedHours > teachingComponent ? 'negative' : assignedHours === teachingComponent ? 'positive' : 'blue-grey-6'"
              text-color="white"
              icon="schedule"
            >
              {{ assignedHours }}h / {{ teachingComponent }}h
              <q-tooltip>Horas letivas atribuídas / componente letiva total</q-tooltip>
            </q-chip>
            <q-chip v-else-if="assignedHours > 0" dense square color="blue-grey-6" text-color="white" icon="schedule">
              {{ assignedHours }}h atribuídas
            </q-chip>
          </div>
          <q-space />
          <q-select
            v-model="curriculumYear"
            :options="yearOptions"
            label="Ano Letivo"
            emit-value map-options dense outlined
            style="min-width:160px"
            @update:model-value="loadCurriculum"
            class="q-mr-md"
          />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <!-- No subjects warning -->
        <q-card-section v-if="!selectedTeacher?.subject_ids?.length" class="text-center q-py-xl">
          <q-icon name="warning" color="warning" size="48px" />
          <div class="q-mt-sm text-subtitle1">Este professor não tem disciplinas configuradas.</div>
          <div class="text-caption text-grey-6 q-mb-md">Adicione primeiro as disciplinas que o professor leciona.</div>
          <q-btn color="secondary" icon="book" label="Gerir disciplinas" unelevated @click="curriculumDialog=false; openSubjects(selectedTeacher!)" />
        </q-card-section>

        <template v-else-if="curriculumYear">
          <!-- Subject selector + defaults -->
          <q-card-section class="q-pt-sm q-pb-xs">
            <div class="row items-center q-gutter-xs q-mb-sm flex-wrap">
              <span class="text-caption text-grey-7">Disciplina:</span>
              <q-chip
                v-for="subId in selectedTeacher!.subject_ids"
                :key="subId"
                clickable dense
                :color="curriculumSubjectId === subId ? 'teal' : 'grey-3'"
                :text-color="curriculumSubjectId === subId ? 'white' : 'dark'"
                @click="curriculumSubjectId = subId"
              >{{ subjectName(subId) }}</q-chip>
            </div>

            <div class="row items-center q-gutter-md">
              <q-input
                v-model.number="defaultHours"
                label="Horas/semana (novas entradas)"
                type="number" min="1" max="20"
                dense outlined style="max-width:240px"
              />
              <q-chip icon="check_circle" color="teal" text-color="white" :label="`${assignedClassCount} turmas atribuídas`" dense />
              <q-space />
              <q-btn flat dense size="sm" color="teal" icon="done_all" label="Atribuir todas" @click="assignAllClasses" />
              <q-btn flat dense size="sm" color="grey" icon="remove_done" label="Remover todas" @click="removeAllClasses" class="q-ml-xs" />
            </div>
          </q-card-section>

          <q-separator />

          <q-card-section class="q-pt-sm" style="max-height:60vh;overflow-y:auto">
            <q-input v-model="curriculumClassSearch" dense outlined clearable placeholder="Pesquisar turma..." class="q-mb-sm">
              <template #prepend><q-icon name="search" /></template>
            </q-input>

            <div v-if="curriculumLoading" class="text-center q-py-xl">
              <q-spinner color="teal" size="40px" />
            </div>

            <div v-else-if="curriculumClassGroups.length === 0" class="text-grey-6 text-caption text-center q-py-xl">
              Sem turmas para este ano letivo
            </div>

            <div v-for="group in curriculumClassGroups" :key="group.school_id" class="q-mb-lg">
              <div class="row items-center q-mb-sm">
                <q-icon name="school" color="grey-5" size="sm" class="q-mr-xs" />
                <span class="text-subtitle2 text-grey-8">{{ group.school_name }}</span>
                <q-badge
                  :color="group.assignedCount === group.classes.length ? 'positive' : group.assignedCount > 0 ? 'warning' : 'grey-4'"
                  :text-color="group.assignedCount === group.classes.length ? 'white' : 'dark'"
                  :label="`${group.assignedCount}/${group.classes.length}`"
                  class="q-ml-sm"
                />
                <q-space />
                <q-btn flat dense size="xs" color="teal" label="Todas" @click="assignSchoolClasses(group.classes)" />
              </div>

              <div class="row q-gutter-sm">
                <q-card
                  v-for="cls in group.classes"
                  :key="cls.id"
                  flat bordered
                  clickable
                  :class="isClassAssigned(cls.id) ? 'bg-teal-1 border-teal' : ''"
                  style="min-width:110px;max-width:130px"
                  @click="toggleClass(cls)"
                >
                  <q-card-section class="q-pa-sm text-center">
                    <q-checkbox
                      :model-value="isClassAssigned(cls.id)"
                      color="teal" dense
                      @click.stop
                      @update:model-value="(v) => toggleClass(cls, v)"
                    />
                    <div class="text-weight-medium q-mt-xs">{{ cls.name }}</div>
                    <div class="text-caption text-grey-6">{{ cls.year_level }}.º ano</div>
                    <q-badge
                      v-if="getClassOtherTeacher(cls.id)"
                      color="orange-2" text-color="dark"
                      :label="getClassOtherTeacher(cls.id)!"
                      class="q-mt-xs"
                      style="max-width:110px;white-space:normal;word-break:break-word"
                    />
                  </q-card-section>
                </q-card>
              </div>
            </div>
          </q-card-section>
        </template>

        <q-card-section v-else class="text-grey text-center q-py-xl">
          Selecione um ano letivo
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Availability dialog -->
    <q-dialog v-model="availabilityDialog" full-width>
      <q-card>
        <q-card-section class="row items-center">
          <div class="text-h6">Disponibilidade: {{ selectedTeacher?.name }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-select v-model="availYear" :options="yearOptions" label="Ano Letivo" emit-value map-options class="q-mb-md" style="max-width:200px" @update:model-value="loadAvailability" />
          <div class="timetable-grid" v-if="availYear">
            <table style="border-collapse:collapse;width:100%">
              <thead>
                <tr>
                  <th style="padding:4px 8px;border:1px solid #ddd;background:#2c3e50;color:white">Tempo</th>
                  <th v-for="day in DAYS" :key="day" style="padding:4px 8px;border:1px solid #ddd;background:#2c3e50;color:white">{{ day }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="slot in uniqueSlots" :key="slot">
                  <td style="padding:4px 8px;border:1px solid #ddd;text-align:center;font-weight:bold">{{ slot }}</td>
                  <td v-for="(day, dayIdx) in DAYS" :key="dayIdx" style="padding:4px;border:1px solid #ddd;text-align:center">
                    <q-checkbox
                      :model-value="isAvailable(dayIdx, slot)"
                      @update:model-value="toggleAvailability(dayIdx, slot)"
                      color="positive"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="row justify-end q-mt-md">
              <q-btn color="primary" label="Guardar disponibilidade" @click="saveAvailability" />
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useTeachersStore, type Teacher } from 'stores/teachers'
import { useClustersStore } from 'stores/clusters'
import { useSchoolsStore } from 'stores/schools'
import { useAcademicYearsStore } from 'stores/academicYears'
import { useSubjectsStore } from 'stores/subjects'
import { useClassesStore, type SchoolClass } from 'stores/classes'
import { api } from 'boot/axios'
import ImportDialog from 'components/ImportDialog.vue'

const $q = useQuasar()
const teachersStore = useTeachersStore()
const clustersStore = useClustersStore()
const classesStore = useClassesStore()

const search = ref('')
const showImport = ref(false)
const bulkAvailDialog = ref(false)
const bulkAvailYear = ref<number | null>(null)
const bulkAvailLoading = ref(false)
const bulkAvailSaving = ref(false)
const bulkBlockedMap = reactive<Record<string, boolean>>({})
const bulkAvailRawSlots = ref<{ slot_number: number; start_time: string; end_time: string }[]>([])
const selectedClusterId = computed(() => clustersStore.clusters[0]?.id ?? null)
const schoolsStore = useSchoolsStore()
const yearsStore = useAcademicYearsStore()
const subjectsStore = useSubjectsStore()

const DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

const columns = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left' as const, sortable: true },
  { name: 'primary_school', label: 'Escola Base', field: 'primary_school_name', align: 'left' as const, sortable: true },
  { name: 'subject_names', label: 'Disciplinas', field: 'subject_names', align: 'left' as const },
  { name: 'teaching_component', label: 'Comp. Letiva', field: 'teaching_component', align: 'center' as const },
  { name: 'max_daily_lessons', label: 'Máx/dia', field: 'max_daily_lessons', align: 'center' as const },
  { name: 'preferred_free_day', label: 'Dia livre', field: 'preferred_free_day', align: 'center' as const },
  { name: 'actions', label: 'Ações', field: 'actions', align: 'center' as const },
]

const dayOptions = DAYS.map((d, i) => ({ label: d, value: i }))
const shiftOptions = [
  { label: 'Manhã (preferência)', value: 'morning' },
  { label: 'Tarde (preferência)', value: 'afternoon' },
]
const dialog = ref(false)
const editing = ref<null | Teacher>(null)
const form = ref({
  cluster_id: null as number | null,
  name: '',
  email: '',
  max_daily_lessons: 5,
  preferred_free_day: null as number | null,
  min_start_slot: null as number | null,
  max_end_slot: null as number | null,
  preferred_shift: null as string | null,
  max_consecutive_lessons: null as number | null,
  teaching_component: null as number | null,
})

// Row expansion
const expandedTeacherId = ref<number | null>(null)
const expandedClasses = ref<{ class_id: number; class_name: string; year_level: number }[]>([])
const expandLoading = ref(false)
const expandCache = reactive<Record<number, { class_id: number; class_name: string; year_level: number }[]>>({})

async function toggleTeacherExpand(teacher: Teacher) {
  if (expandedTeacherId.value === teacher.id) {
    expandedTeacherId.value = null
    return
  }
  expandedTeacherId.value = teacher.id
  if (expandCache[teacher.id]) {
    expandedClasses.value = expandCache[teacher.id]
    return
  }
  expandLoading.value = true
  try {
    const activeYearId = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id
    const params: Record<string, unknown> = {}
    if (activeYearId) params.academic_year_id = activeYearId
    const { data } = await api.get<{ class_id: number; class_name: string; year_level: number }[]>(
      `/teachers/${teacher.id}/curriculum`,
      { params }
    )
    const seen = new Map<number, { class_id: number; class_name: string; year_level: number }>()
    for (const e of data) {
      if (!seen.has(e.class_id)) seen.set(e.class_id, e)
    }
    const deduped = [...seen.values()].sort((a, b) => a.year_level - b.year_level || a.class_name.localeCompare(b.class_name))
    expandCache[teacher.id] = deduped
    expandedClasses.value = deduped
  } finally {
    expandLoading.value = false
  }
}

// School filter
const selectedSchoolIds = reactive(new Set<number>())
function toggleSchoolFilter(id: number) {
  if (selectedSchoolIds.has(id)) selectedSchoolIds.delete(id)
  else selectedSchoolIds.add(id)
}
const filteredTeachers = computed(() => {
  if (selectedSchoolIds.size === 0) return teachersStore.teachers
  return teachersStore.teachers.filter((t) =>
    (t.school_ids ?? []).some((sid) => selectedSchoolIds.has(sid))
  )
})

const clusterOptions = computed(() => clustersStore.clusters.map((c) => ({ label: c.name, value: c.id })))
const schoolOptions = computed(() => schoolsStore.schools.map((s) => ({ label: s.name, value: s.id })))
const yearOptions = computed(() => yearsStore.years.map((y) => ({ label: y.name, value: y.id })))

// Schools
const schoolsDialog = ref(false)
const selectedTeacher = ref<Teacher | null>(null)
const schoolAssignments = ref<{ id: number; school_id: number; school_name?: string | null; academic_year_id: number; travel_time_minutes: number; is_primary: boolean }[]>([])
const newAssignment = ref({ school_id: null as number | null, academic_year_id: null as number | null, travel_time_minutes: 0, is_primary: false })

function schoolName(id: number) { return schoolsStore.schools.find((s) => s.id === id)?.name ?? '—' }
function yearName(id: number) { return yearsStore.years.find((y) => y.id === id)?.name ?? '—' }

// Subjects
const subjectsDialog = ref(false)
const teacherSubjects = ref<{ id: number; teacher_id: number; subject_id: number }[]>([])
const newSubjectId = ref<number | null>(null)

function subjectName(id: number) { return subjectsStore.subjects.find((s) => s.id === id)?.name ?? '—' }
const availableSubjectOptions = computed(() => {
  const assigned = new Set(teacherSubjects.value.map((ts) => ts.subject_id))
  return subjectsStore.subjects.filter((s) => !assigned.has(s.id)).map((s) => ({ label: s.name, value: s.id }))
})

// Curriculum assignment
type CurriculumEntry = {
  id: number
  class_id: number
  class_name: string
  year_level: number
  school_id: number | null
  subject_id: number
  subject_name: string
  hours_per_week: number
  teacher_id: number | null
  teacher_name: string | null
}

const curriculumDialog = ref(false)
const curriculumLoading = ref(false)
const curriculumYear = ref<number | null>(null)
const curriculumSubjectId = ref<number | null>(null)
const defaultHours = ref(2)
const curriculumClassSearch = ref('')
// All curriculum entries for the cluster+year (to detect existing entries per class+subject)
const allClusterEntries = ref<CurriculumEntry[]>([])

const clusterId = computed(() => clustersStore.clusters[0]?.id ?? null)

// All classes in the cluster for the curriculum year
const curriculumAllClasses = computed<SchoolClass[]>(() => {
  const schoolIds = new Set(schoolsStore.schools.filter((s) => s.cluster_id === clusterId.value).map((s) => s.id))
  return classesStore.classes.filter(
    (c) => c.academic_year_id === curriculumYear.value && schoolIds.has(c.school_id)
  )
})

// Map class_id → CurriculumEntry for the selected subject (quick lookup)
const classEntryMap = computed(() => {
  const map = new Map<number, CurriculumEntry>()
  if (!curriculumSubjectId.value) return map
  for (const e of allClusterEntries.value) {
    if (e.subject_id === curriculumSubjectId.value) map.set(e.class_id, e)
  }
  return map
})

function isClassAssigned(classId: number): boolean {
  const e = classEntryMap.value.get(classId)
  return !!(e && e.teacher_id === selectedTeacher.value?.id)
}

function getClassOtherTeacher(classId: number): string | null {
  const e = classEntryMap.value.get(classId)
  if (!e || !e.teacher_id || e.teacher_id === selectedTeacher.value?.id) return null
  return teacherName(e.teacher_id)
}

// Classes grouped by school with search filter + assigned counts
const curriculumClassGroups = computed(() => {
  const txt = curriculumClassSearch.value.toLowerCase()
  const filtered = curriculumAllClasses.value.filter(
    (c) => !txt || c.name.toLowerCase().includes(txt) || String(c.year_level).includes(txt)
  )
  const bySchool = new Map<number, SchoolClass[]>()
  for (const c of filtered) {
    if (!bySchool.has(c.school_id)) bySchool.set(c.school_id, [])
    bySchool.get(c.school_id)!.push(c)
  }
  return [...bySchool.entries()]
    .map(([schoolId, classes]) => ({
      school_id: schoolId,
      school_name: schoolsStore.schools.find((s) => s.id === schoolId)?.name ?? '—',
      classes: classes.sort((a, b) => a.year_level - b.year_level || a.name.localeCompare(b.name)),
      assignedCount: classes.filter((c) => isClassAssigned(c.id)).length,
    }))
    .sort((a, b) => a.school_name.localeCompare(b.school_name))
})

const assignedClassCount = computed(() =>
  curriculumAllClasses.value.filter((c) => isClassAssigned(c.id)).length
)

// Total hours assigned to this teacher across all subjects this year
const assignedHours = computed(() => {
  if (!selectedTeacher.value) return 0
  return allClusterEntries.value
    .filter((e) => e.teacher_id === selectedTeacher.value!.id)
    .reduce((sum, e) => sum + (e.hours_per_week ?? 0), 0)
})

const teachingComponent = computed(() => selectedTeacher.value?.teaching_component ?? null)

function teacherName(id: number | null) {
  if (!id) return ''
  return teachersStore.teachers.find((t) => t.id === id)?.name ?? '?'
}

async function openCurriculum(teacher: Teacher) {
  selectedTeacher.value = teacher
  curriculumYear.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  curriculumSubjectId.value = teacher.subject_ids?.[0] ?? null
  curriculumClassSearch.value = ''
  curriculumDialog.value = true
  if (curriculumYear.value) await loadCurriculum()
}

async function loadCurriculum() {
  if (!clusterId.value || !curriculumYear.value) return
  curriculumLoading.value = true
  try {
    const [entriesRes] = await Promise.all([
      api.get<CurriculumEntry[]>('/classes/curriculum-overview', {
        params: { cluster_id: clusterId.value, academic_year_id: curriculumYear.value },
      }),
      classesStore.fetchAll({ academic_year_id: curriculumYear.value }),
    ])
    allClusterEntries.value = entriesRes.data
  } finally {
    curriculumLoading.value = false
  }
}

async function toggleClass(cls: SchoolClass, forceAssign?: boolean) {
  if (!curriculumSubjectId.value || !selectedTeacher.value) return
  const shouldAssign = forceAssign !== undefined ? forceAssign : !isClassAssigned(cls.id)
  const existing = classEntryMap.value.get(cls.id)

  if (shouldAssign) {
    if (existing) {
      if (existing.teacher_id && existing.teacher_id !== selectedTeacher.value.id) {
        $q.dialog({
          title: 'Substituir professor',
          message: `${cls.name} já tem "${teacherName(existing.teacher_id)}" atribuído. Substituir?`,
          ok: { label: 'Substituir', color: 'warning' }, cancel: true,
        }).onOk(() => doUpdateEntry(existing, selectedTeacher.value!.id))
        return
      }
      await doUpdateEntry(existing, selectedTeacher.value.id)
    } else {
      await doCreateEntry(cls)
    }
  } else {
    if (existing && existing.teacher_id === selectedTeacher.value.id) {
      await doUpdateEntry(existing, null)
    }
  }
}

async function doUpdateEntry(entry: CurriculumEntry, teacherId: number | null) {
  try {
    await api.put(`/classes/curriculum/${entry.id}`, { teacher_id: teacherId })
    entry.teacher_id = teacherId
    entry.teacher_name = teacherId ? teacherName(teacherId) : null
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: unknown } } }
    const status = err?.response?.status ?? '?'
    const detail = err?.response?.data?.detail
    const msg = detail ? (typeof detail === 'string' ? detail : JSON.stringify(detail)) : 'Sem detalhe'
    console.error('[doUpdateEntry] HTTP', status, detail)
    $q.notify({ type: 'negative', message: `Erro ${status} ao atualizar entrada`, caption: msg, timeout: 8000 })
  }
}

async function doCreateEntry(cls: SchoolClass) {
  if (!curriculumSubjectId.value || !selectedTeacher.value) return
  try {
    const { data } = await api.post<{ id: number }>(`/classes/${cls.id}/curriculum`, {
      class_id: cls.id,
      subject_id: curriculumSubjectId.value,
      hours_per_week: defaultHours.value,
      teacher_id: selectedTeacher.value.id,
    })
    const subj = subjectsStore.subjects.find((s) => s.id === curriculumSubjectId.value)
    allClusterEntries.value = [...allClusterEntries.value, {
      id: data.id,
      class_id: cls.id,
      class_name: cls.name,
      year_level: cls.year_level,
      school_id: cls.school_id,
      subject_id: curriculumSubjectId.value!,
      subject_name: subj?.name ?? '',
      hours_per_week: defaultHours.value,
      teacher_id: selectedTeacher.value.id,
      teacher_name: selectedTeacher.value.name,
    }]
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: unknown } } }
    const status = err?.response?.status ?? '?'
    const detail = err?.response?.data?.detail
    const msg = detail
      ? (typeof detail === 'string' ? detail : JSON.stringify(detail))
      : 'Sem detalhe'
    console.error('[doCreateEntry] HTTP', status, detail)
    $q.notify({
      type: 'negative',
      message: `Erro ${status} ao criar entrada curricular`,
      caption: msg,
      timeout: 8000,
    })
  }
}

async function assignAllClasses() {
  for (const cls of curriculumAllClasses.value) {
    if (!isClassAssigned(cls.id)) await toggleClass(cls, true)
  }
}

async function removeAllClasses() {
  for (const cls of curriculumAllClasses.value) {
    if (isClassAssigned(cls.id)) await toggleClass(cls, false)
  }
}

async function assignSchoolClasses(classes: SchoolClass[]) {
  for (const cls of classes) {
    if (!isClassAssigned(cls.id)) await toggleClass(cls, true)
  }
}

// Availability
const availabilityDialog = ref(false)
const availYear = ref<number | null>(null)
const availabilityMap = reactive<Record<string, boolean>>({})
const uniqueSlots = ref<number[]>([])

function isAvailable(day: number, slot: number) {
  return availabilityMap[`${day}_${slot}`] !== false
}

function toggleAvailability(day: number, slot: number) {
  const key = `${day}_${slot}`
  availabilityMap[key] = !isAvailable(day, slot)
}

onMounted(async () => {
  await Promise.all([
    teachersStore.fetchAll(),
    clustersStore.fetchAll(),
    schoolsStore.fetchAll(),
    yearsStore.fetchAll(),
    subjectsStore.fetchAll(),
  ])
})

function openCreate() {
  editing.value = null
  form.value = {
    cluster_id: clustersStore.clusters[0]?.id ?? null,
    name: '',
    email: '',
    max_daily_lessons: 5,
    preferred_free_day: null,
    min_start_slot: null,
    max_end_slot: null,
    preferred_shift: null,
    max_consecutive_lessons: null,
    teaching_component: null,
  }
  dialog.value = true
}

function openEdit(row: Teacher) {
  editing.value = row
  form.value = {
    cluster_id: row.cluster_id,
    name: row.name,
    email: row.email || '',
    max_daily_lessons: row.max_daily_lessons,
    preferred_free_day: row.preferred_free_day ?? null,
    min_start_slot: row.min_start_slot ?? null,
    max_end_slot: row.max_end_slot ?? null,
    preferred_shift: row.preferred_shift ?? null,
    max_consecutive_lessons: row.max_consecutive_lessons ?? null,
    teaching_component: row.teaching_component ?? null,
  }
  dialog.value = true
}

async function save() {
  try {
    if (editing.value) {
      const payload = {
        name: form.value.name,
        email: form.value.email || null,
        max_daily_lessons: form.value.max_daily_lessons,
        preferred_free_day: form.value.preferred_free_day,
        min_start_slot: form.value.min_start_slot,
        max_end_slot: form.value.max_end_slot,
        preferred_shift: form.value.preferred_shift,
        max_consecutive_lessons: form.value.max_consecutive_lessons,
        teaching_component: form.value.teaching_component,
      }
      await teachersStore.update(editing.value.id, payload)
      $q.notify({ type: 'positive', message: 'Atualizado' })
    } else {
      if (!form.value.cluster_id) return
      await teachersStore.create({ ...form.value, cluster_id: form.value.cluster_id } as Parameters<typeof teachersStore.create>[0])
      $q.notify({ type: 'positive', message: 'Criado' })
    }
    dialog.value = false
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erro ao guardar'
    $q.notify({ type: 'negative', message: String(msg) })
  }
}

async function openSchools(teacher: Teacher) {
  selectedTeacher.value = teacher
  schoolAssignments.value = await teachersStore.fetchSchoolAssignments(teacher.id)
  schoolsDialog.value = true
}

async function addSchoolAssignment() {
  if (!selectedTeacher.value || !newAssignment.value.school_id || !newAssignment.value.academic_year_id) return
  try {
    const data = await teachersStore.addSchoolAssignment(selectedTeacher.value.id, {
      school_id: newAssignment.value.school_id,
      academic_year_id: newAssignment.value.academic_year_id,
      travel_time_minutes: newAssignment.value.travel_time_minutes,
      is_primary: newAssignment.value.is_primary,
    })
    if (newAssignment.value.is_primary) {
      schoolAssignments.value.forEach((a) => { a.is_primary = false })
    }
    schoolAssignments.value.push(data)
    newAssignment.value = { school_id: null, academic_year_id: null, travel_time_minutes: 0, is_primary: false }
    $q.notify({ type: 'positive', message: 'Escola adicionada' })
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
    const msg = detail ? (typeof detail === 'string' ? detail : JSON.stringify(detail)) : 'Erro ao adicionar escola'
    $q.notify({ type: 'negative', message: String(msg) })
  }
}

async function setPrimarySchool(assignmentId: number) {
  try {
    await teachersStore.setPrimarySchool(assignmentId)
    schoolAssignments.value.forEach((a) => { a.is_primary = a.id === assignmentId })
    $q.notify({ type: 'positive', message: 'Escola base definida' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao definir escola base' })
  }
}

async function removeSchoolAssignment(id: number) {
  try {
    await teachersStore.removeSchoolAssignment(id)
    schoolAssignments.value = schoolAssignments.value.filter((a) => a.id !== id)
    $q.notify({ type: 'positive', message: 'Removido' })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao remover' })
  }
}

async function openSubjects(teacher: Teacher) {
  selectedTeacher.value = teacher
  teacherSubjects.value = await teachersStore.fetchSubjects(teacher.id)
  subjectsDialog.value = true
}

async function addSubject() {
  if (!selectedTeacher.value || !newSubjectId.value) return
  const data = await teachersStore.addSubject(selectedTeacher.value.id, newSubjectId.value)
  teacherSubjects.value.push(data)
  newSubjectId.value = null
}

async function removeSubject(subjectId: number) {
  if (!selectedTeacher.value) return
  await teachersStore.removeSubject(selectedTeacher.value.id, subjectId)
  teacherSubjects.value = teacherSubjects.value.filter((ts) => ts.subject_id !== subjectId)
}

async function openAvailability(teacher: Teacher) {
  selectedTeacher.value = teacher
  availYear.value = yearsStore.years.find((y) => y.is_active)?.id ?? null
  availabilityDialog.value = true
  if (availYear.value) await loadAvailability()
}

async function loadAvailability() {
  if (!selectedTeacher.value || !availYear.value) return
  const slots = await api.get('/time-slots', { params: { academic_year_id: availYear.value } })
  const slotNums = [...new Set((slots.data as { slot_number: number }[]).map((s) => s.slot_number))].sort((a, b) => a - b)
  uniqueSlots.value = slotNums

  const avail = await teachersStore.fetchAvailability(selectedTeacher.value.id, availYear.value)
  // Clear previous state
  Object.keys(availabilityMap).forEach((k) => delete availabilityMap[k])
  // Default all available
  for (let d = 0; d < 5; d++) {
    for (const s of slotNums) {
      availabilityMap[`${d}_${s}`] = true
    }
  }
  for (const a of avail) {
    availabilityMap[`${a.day_of_week}_${a.slot_number}`] = a.is_available
  }
}

async function saveAvailability() {
  if (!selectedTeacher.value || !availYear.value) return
  const teacherId = selectedTeacher.value.id
  const yearId = availYear.value
  const availabilities: { teacher_id: number; academic_year_id: number; day_of_week: number; slot_number: number; is_available: boolean }[] = []
  for (let d = 0; d < 5; d++) {
    for (const s of uniqueSlots.value) {
      availabilities.push({
        teacher_id: teacherId,
        academic_year_id: yearId,
        day_of_week: d,
        slot_number: s,
        is_available: isAvailable(d, s),
      })
    }
  }
  try {
    await teachersStore.setAvailabilityBulk(teacherId, yearId, availabilities)
    const blocked = availabilities.filter((a) => !a.is_available).length
    $q.notify({
      type: 'positive',
      message: blocked
        ? `Disponibilidade guardada — ${blocked} bloco(s) indisponível(eis)`
        : 'Disponibilidade guardada — todos os blocos disponíveis',
    })
    await loadAvailability()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    const status = e?.response?.status as number | undefined
    const msg = typeof detail === 'string' ? detail
      : status ? `Erro ${status} ao guardar disponibilidade`
      : 'Erro ao guardar disponibilidade'
    $q.notify({ type: 'negative', message: msg })
  }
}

const bulkUniqueSlots = computed(() => {
  const seen = new Map<number, { slot_number: number; start_time: string; end_time: string }>()
  for (const s of bulkAvailRawSlots.value) {
    if (!seen.has(s.slot_number)) seen.set(s.slot_number, s)
  }
  return [...seen.values()].sort((a, b) => a.slot_number - b.slot_number)
})

const bulkBlockedCount = computed(() => Object.values(bulkBlockedMap).filter(Boolean).length)

function isBulkBlocked(day: number, slot: number) {
  return bulkBlockedMap[`${day}_${slot}`] === true
}

function toggleBulkSlot(day: number, slot: number) {
  const key = `${day}_${slot}`
  if (bulkBlockedMap[key]) delete bulkBlockedMap[key]
  else bulkBlockedMap[key] = true
}

function clearBulkSlots() {
  Object.keys(bulkBlockedMap).forEach((k) => delete bulkBlockedMap[k])
}

async function openBulkAvail() {
  bulkAvailYear.value = yearsStore.years.find((y) => y.is_active)?.id ?? yearsStore.years[0]?.id ?? null
  bulkAvailDialog.value = true
  if (bulkAvailYear.value) await loadBulkSlots()
}

async function loadBulkSlots() {
  if (!bulkAvailYear.value) return
  bulkAvailLoading.value = true
  try {
    const { data } = await api.get('/time-slots', { params: { academic_year_id: bulkAvailYear.value } })
    bulkAvailRawSlots.value = (data as { slot_number: number; start_time: string; end_time: string }[])
  } finally {
    bulkAvailLoading.value = false
  }
}

async function applyBulkAvail() {
  const clusterId = selectedClusterId.value
  if (!clusterId || !bulkAvailYear.value) {
    $q.notify({ type: 'warning', message: 'Selecione um agrupamento e ano letivo.' })
    return
  }
  bulkAvailSaving.value = true
  try {
    const blocked = Object.entries(bulkBlockedMap)
      .filter(([, v]) => v)
      .map(([key]) => {
        const [d, s] = key.split('_').map(Number)
        return { day_of_week: d, slot_number: s }
      })
    const res = await teachersStore.bulkAvailability(clusterId, bulkAvailYear.value, blocked)
    $q.notify({ type: 'positive', message: res.message })
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao aplicar disponibilidade.' })
  } finally {
    bulkAvailSaving.value = false
  }
}

function confirmDelete(row: Teacher) {
  $q.dialog({
    title: 'Confirmar eliminação',
    message: `Eliminar "${row.name}"?`,
    ok: { label: 'Eliminar', color: 'negative' },
    cancel: true,
  }).onOk(async () => {
    await teachersStore.remove(row.id)
    $q.notify({ type: 'positive', message: 'Eliminado' })
  })
}
</script>

<style scoped>
.bulk-avail-grid-wrap {
  overflow-x: auto;
}
.bulk-avail-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 480px;
}
.bulk-avail-th {
  padding: 6px 12px;
  border: 1px solid #ddd;
  background: #2c3e50;
  color: white;
  text-align: center;
  font-size: 13px;
}
.bulk-avail-th--slot {
  min-width: 120px;
  text-align: left;
}
.bulk-avail-td {
  border: 1px solid #ddd;
  padding: 4px 8px;
}
.bulk-avail-td--label {
  white-space: nowrap;
  font-size: 13px;
}
.bulk-avail-td--cell {
  text-align: center;
  cursor: pointer;
  transition: background 0.12s;
  min-width: 80px;
}
.bulk-avail-td--cell:hover {
  background: rgba(0, 0, 0, 0.06);
}
.bulk-avail-td--blocked {
  background: #e53935 !important;
}
.body--dark .bulk-avail-th {
  background: #1a2332;
}
.body--dark .bulk-avail-td {
  border-color: #444;
}
.body--dark .bulk-avail-td--cell:hover {
  background: rgba(255, 255, 255, 0.08);
}
</style>
