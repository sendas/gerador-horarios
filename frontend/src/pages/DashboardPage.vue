<template>
  <q-page>
    <!-- Hero -->
    <div class="dash-hero">
      <div class="dash-hero__inner">
        <q-icon name="hub" size="56px" class="dash-hero__icon" />
        <div class="dash-hero__title">Sinaptik</div>
        <div class="dash-hero__tag">Plataforma Inteligente de Horários Escolares</div>
        <div class="dash-hero__sub">
          O sistema mais completo para criação automática de horários para agrupamentos — geração por IA, sem conflitos, em segundos.
        </div>
      </div>
    </div>

    <div class="q-pa-md">
      <!-- Stats -->
      <div class="row q-col-gutter-md q-mb-xl">
        <div class="col-6 col-sm-3" v-for="stat in stats" :key="stat.label">
          <q-card flat bordered class="stat-card">
            <q-card-section class="row items-center no-wrap q-pa-md">
              <div class="col">
                <div class="text-overline text-grey-6">{{ stat.label }}</div>
                <div class="text-h4 text-weight-bold" :style="{ color: stat.color }">{{ stat.value }}</div>
              </div>
              <q-icon :name="stat.icon" size="40px" :color="stat.color" style="opacity:0.25" />
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Quick links -->
      <div class="text-subtitle1 text-weight-bold q-mb-md">Acesso Rápido</div>
      <div class="row q-col-gutter-md q-mb-xl">
        <div class="col-6 col-sm-4 col-md-3" v-for="link in quickLinks" :key="link.to">
          <q-card flat bordered class="link-card" clickable v-ripple @click="router.push(link.to)">
            <q-card-section class="column items-center text-center q-pa-md">
              <q-icon :name="link.icon" :color="link.color" size="32px" class="q-mb-sm" />
              <div class="text-body2 text-weight-medium">{{ link.label }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Copyright -->
      <div class="text-caption text-center text-grey-5 q-pb-md">
        © {{ new Date().getFullYear() }} Sinaptik — Plataforma Inteligente de Horários · Desenvolvido com
        <q-icon name="auto_awesome" size="xs" color="deep-purple-4" /> Claude AI ·
        <a href="https://github.com/sendas/gerador-horarios" target="_blank" class="text-grey-5">GitHub</a>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from 'boot/axios'

const router = useRouter()

const stats = ref([
  { label: 'Professores', value: 0, icon: 'person',      color: 'deep-orange-6' },
  { label: 'Turmas',      value: 0, icon: 'group',       color: 'blue-7' },
  { label: 'Escolas',     value: 0, icon: 'school',      color: 'teal-6' },
  { label: 'Horários',    value: 0, icon: 'table_chart', color: 'green-7' },
])

const quickLinks = [
  { to: '/timetables',      icon: 'table_chart',  label: 'Horários',       color: 'green-7' },
  { to: '/teachers',        icon: 'person',       label: 'Professores',    color: 'deep-orange-6' },
  { to: '/classes',         icon: 'group',        label: 'Turmas',         color: 'blue-7' },
  { to: '/subjects',        icon: 'book',         label: 'Disciplinas',    color: 'purple-7' },
  { to: '/schools',         icon: 'school',       label: 'Escolas',        color: 'teal-6' },
  { to: '/scheduling-rules',icon: 'rule',         label: 'Regras',         color: 'red-6' },
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
  } catch { /* backend may not be running */ }
})
</script>

<style scoped>
.dash-hero {
  background: linear-gradient(135deg, #1a237e 0%, #283593 25%, #1565c0 60%, #0277bd 100%);
  padding: 48px 24px 40px;
  text-align: center;
  color: #fff;
  margin-bottom: 0;
}
.dash-hero__inner { max-width: 600px; margin: 0 auto; }
.dash-hero__icon { opacity: 0.9; margin-bottom: 12px; }
.dash-hero__title {
  font-size: 2.4rem;
  font-weight: 800;
  letter-spacing: -1px;
  margin-bottom: 6px;
}
.dash-hero__tag {
  font-size: 0.95rem;
  font-weight: 600;
  opacity: 0.85;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}
.dash-hero__sub {
  font-size: 0.88rem;
  opacity: 0.72;
  line-height: 1.6;
  max-width: 480px;
  margin: 0 auto;
}

.stat-card { border-radius: 10px !important; }
.link-card {
  border-radius: 10px !important;
  transition: transform 0.15s, box-shadow 0.15s;
  cursor: pointer;
}
.link-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.1) !important;
}
</style>
