<template>
  <q-page padding>
    <div class="text-h5 q-mb-lg">Dashboard</div>

    <div class="row q-col-gutter-md q-mb-xl">
      <div class="col-12 col-sm-6 col-md-3" v-for="stat in stats" :key="stat.label">
        <q-card>
          <q-card-section class="row items-center no-wrap">
            <div class="col">
              <div class="text-overline">{{ stat.label }}</div>
              <div class="text-h4 text-weight-bold text-primary">{{ stat.value }}</div>
            </div>
            <q-icon :name="stat.icon" size="48px" color="grey-4" />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div class="text-h6 q-mb-md">Acesso Rápido</div>
    <div class="row q-col-gutter-md">
      <div class="col-6 col-sm-4 col-md-3" v-for="link in quickLinks" :key="link.to">
        <q-btn
          :to="link.to"
          :icon="link.icon"
          :label="link.label"
          color="primary"
          outline
          class="full-width"
          size="md"
        />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from 'boot/axios'

const stats = ref([
  { label: 'Professores', value: 0, icon: 'person' },
  { label: 'Turmas', value: 0, icon: 'group' },
  { label: 'Escolas', value: 0, icon: 'school' },
  { label: 'Horários', value: 0, icon: 'table_chart' },
])

const quickLinks = [
  { to: '/clusters', icon: 'domain', label: 'Agrupamentos' },
  { to: '/schools', icon: 'school', label: 'Escolas' },
  { to: '/teachers', icon: 'person', label: 'Professores' },
  { to: '/classes', icon: 'group', label: 'Turmas' },
  { to: '/timetables', icon: 'table_chart', label: 'Horários' },
  { to: '/subjects', icon: 'book', label: 'Disciplinas' },
]

onMounted(async () => {
  try {
    const [teachers, classes, schools, timetables] = await Promise.all([
      api.get('/teachers').then(r => r.data.length),
      api.get('/classes').then(r => r.data.length),
      api.get('/schools').then(r => r.data.length),
      api.get('/timetables').then(r => r.data.length),
    ])
    stats.value[0].value = teachers
    stats.value[1].value = classes
    stats.value[2].value = schools
    stats.value[3].value = timetables
  } catch {
    // backend may not be running
  }
})
</script>
