<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" full-width>
    <q-card style="max-width: 680px; width: 100%">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">
          <q-icon name="lock" class="q-mr-sm" color="warning" />
          Bloqueios de Horário
        </div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section class="q-pb-xs text-caption text-grey-7">
        As turmas e professores bloqueados têm os seus horários preservados durante a próxima geração.
        Apenas as entradas <strong>não bloqueadas</strong> serão reagendadas.
      </q-card-section>

      <q-card-section>
        <q-tabs v-model="tab" dense align="left" active-color="primary">
          <q-tab name="teachers" icon="person" label="Professores" />
          <q-tab name="classes" icon="group" label="Turmas" />
        </q-tabs>
        <q-separator />

        <q-tab-panels v-model="tab" animated>
          <!-- Teachers tab -->
          <q-tab-panel name="teachers" class="q-pa-none">
            <q-list separator>
              <q-item v-if="teachers.length === 0" class="text-grey-6 text-center q-pa-lg">
                Sem professores disponíveis
              </q-item>
              <q-item v-for="teacher in teachers" :key="teacher.id" dense>
                <q-item-section avatar>
                  <q-icon
                    :name="isLocked('teacher', teacher.id) ? 'lock' : 'lock_open'"
                    :color="isLocked('teacher', teacher.id) ? 'warning' : 'grey-4'"
                  />
                </q-item-section>
                <q-item-section>{{ teacher.name }}</q-item-section>
                <q-item-section side>
                  <q-toggle
                    :model-value="isLocked('teacher', teacher.id)"
                    @update:model-value="toggle('teacher', teacher.id)"
                    color="warning"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-tab-panel>

          <!-- Classes tab -->
          <q-tab-panel name="classes" class="q-pa-none">
            <q-list separator>
              <q-item v-if="classes.length === 0" class="text-grey-6 text-center q-pa-lg">
                Sem turmas disponíveis
              </q-item>
              <q-item v-for="cls in classes" :key="cls.id" dense>
                <q-item-section avatar>
                  <q-icon
                    :name="isLocked('class', cls.id) ? 'lock' : 'lock_open'"
                    :color="isLocked('class', cls.id) ? 'warning' : 'grey-4'"
                  />
                </q-item-section>
                <q-item-section>{{ cls.name }}</q-item-section>
                <q-item-section side>
                  <q-toggle
                    :model-value="isLocked('class', cls.id)"
                    @update:model-value="toggle('class', cls.id)"
                    color="warning"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <div class="text-caption text-grey-6">
          <q-icon name="info" size="xs" class="q-mr-xs" />
          <span v-if="locks.length === 0">Nenhum bloqueio ativo — toda a geração começa do zero.</span>
          <span v-else>{{ locks.length }} bloqueio(s) ativo(s):
            {{ teacherLocks.length }} professor(es), {{ classLocks.length }} turma(s).</span>
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

interface Lock { id: number; lock_type: string; entity_id: number }

const props = defineProps<{
  modelValue: boolean
  timetableId: number | null
  teachers: { id: number; name: string }[]
  classes: { id: number; name: string }[]
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const $q = useQuasar()
const tab = ref('teachers')
const locks = ref<Lock[]>([])

const teacherLocks = computed(() => locks.value.filter((l) => l.lock_type === 'teacher'))
const classLocks = computed(() => locks.value.filter((l) => l.lock_type === 'class'))

function isLocked(type: string, entityId: number) {
  return locks.value.some((l) => l.lock_type === type && l.entity_id === entityId)
}

async function loadLocks() {
  if (!props.timetableId) return
  const { data } = await api.get<Lock[]>(`/timetables/${props.timetableId}/locks`)
  locks.value = data
}

async function toggle(type: string, entityId: number) {
  if (!props.timetableId) return
  const existing = locks.value.find((l) => l.lock_type === type && l.entity_id === entityId)
  try {
    if (existing) {
      await api.delete(`/timetables/${props.timetableId}/locks/${existing.id}`)
      locks.value = locks.value.filter((l) => l.id !== existing.id)
    } else {
      const { data } = await api.post<Lock>(`/timetables/${props.timetableId}/locks`, {
        lock_type: type,
        entity_id: entityId,
      })
      locks.value.push(data)
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao alterar bloqueio' })
  }
}

watch(
  () => props.modelValue,
  (open) => { if (open) loadLocks() },
)
</script>
