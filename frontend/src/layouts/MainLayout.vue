<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />
        <q-toolbar-title>
          <q-icon name="hub" class="q-mr-sm" />
          Sinaptik
          <span style="font-size:0.65em;opacity:0.75;margin-left:6px;font-weight:400">v{{ appVersion }}</span>
        </q-toolbar-title>

        <!-- Demo badge -->
        <q-chip v-if="auth.isDemo" color="teal-7" text-color="white" icon="explore" label="DEMO" size="sm" class="q-mr-sm" />

        <q-chip
          v-if="auth.user"
          square
          color="white"
          text-color="primary"
          class="q-mr-xs"
          size="sm"
        >
          <q-avatar icon="person" />
          {{ auth.user.full_name || auth.user.username }}
          <q-badge
            v-if="auth.user.role !== 'user'"
            :color="auth.user.role === 'admin' ? 'red-7' : 'grey-6'"
            floating
          >{{ auth.user.role }}</q-badge>
        </q-chip>

        <q-btn flat dense round :icon="$q.dark.isActive ? 'light_mode' : 'dark_mode'" @click="$q.dark.toggle(); saveDarkMode()">
          <q-tooltip>{{ $q.dark.isActive ? 'Modo claro' : 'Modo escuro' }}</q-tooltip>
        </q-btn>

        <q-btn flat dense round icon="logout" @click="handleLogout">
          <q-tooltip>Terminar sessão</q-tooltip>
        </q-btn>
      </q-toolbar>

      <!-- Demo banner -->
      <div v-if="auth.isDemo" class="bg-teal-8 text-white text-center text-caption q-py-xs">
        <q-icon name="info" size="xs" class="q-mr-xs" />
        Modo demonstração — dados de exemplo, alterações não são gravadas permanentemente
      </div>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered>
      <q-list>
        <q-item-label header>Navegação</q-item-label>

        <q-item clickable v-ripple :to="'/'">
          <q-item-section avatar><q-icon name="home" color="blue-7" /></q-item-section>
          <q-item-section>Dashboard</q-item-section>
        </q-item>

        <q-separator />
        <q-item-label header caption>Configuração</q-item-label>

        <q-item clickable v-ripple :to="'/clusters'">
          <q-item-section avatar><q-icon name="domain" color="green-7" /></q-item-section>
          <q-item-section>Agrupamentos</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/schools'">
          <q-item-section avatar><q-icon name="school" color="teal-7" /></q-item-section>
          <q-item-section>Escolas</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/academic-years'">
          <q-item-section avatar><q-icon name="calendar_today" color="orange-7" /></q-item-section>
          <q-item-section>Anos Letivos</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/time-slots'">
          <q-item-section avatar><q-icon name="schedule" color="indigo-6" /></q-item-section>
          <q-item-section>Tempos Letivos</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/scheduling-rules'">
          <q-item-section avatar><q-icon name="rule" color="red-6" /></q-item-section>
          <q-item-section>Regras de Horário</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/rooms'">
          <q-item-section avatar><q-icon name="meeting_room" color="brown-6" /></q-item-section>
          <q-item-section>Salas</q-item-section>
        </q-item>

        <q-separator />
        <q-item-label header caption>Curriculum</q-item-label>

        <q-item clickable v-ripple :to="'/subjects'">
          <q-item-section avatar><q-icon name="book" color="purple-7" /></q-item-section>
          <q-item-section>Disciplinas</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/classes'">
          <q-item-section avatar><q-icon name="group" color="blue-8" /></q-item-section>
          <q-item-section>Turmas</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/curriculum-plans'">
          <q-item-section avatar><q-icon name="menu_book" color="deep-purple-6" /></q-item-section>
          <q-item-section>Planos Curriculares</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/import-curriculum'">
          <q-item-section avatar><q-icon name="upload_file" color="purple-7" /></q-item-section>
          <q-item-section>Importar Currículo</q-item-section>
        </q-item>

        <q-separator />
        <q-item-label header caption>Pessoal</q-item-label>

        <q-item clickable v-ripple :to="'/teachers'">
          <q-item-section avatar><q-icon name="person" color="deep-orange-6" /></q-item-section>
          <q-item-section>Professores</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/teacher-assignment'">
          <q-item-section avatar><q-icon name="assignment_ind" color="teal-7" /></q-item-section>
          <q-item-section>Atribuição de Professores</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/non-teaching'">
          <q-item-section avatar><q-icon name="work_off" color="grey-7" /></q-item-section>
          <q-item-section>Serviço Não Letivo</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/service-distribution'">
          <q-item-section avatar><q-icon name="schedule" color="teal-8" /></q-item-section>
          <q-item-section>Definição de horas por docente</q-item-section>
        </q-item>

        <q-separator />
        <q-item-label header caption>Horários</q-item-label>

        <q-item clickable v-ripple :to="'/timetables'">
          <q-item-section avatar><q-icon name="table_chart" color="green-8" /></q-item-section>
          <q-item-section>Horários</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/service-distribution-report'">
          <q-item-section avatar><q-icon name="bar_chart" color="cyan-7" /></q-item-section>
          <q-item-section>Relatório de Serviço</q-item-section>
        </q-item>

        <template v-if="auth.isAdmin">
          <q-separator />
          <q-item-label header caption>Administração</q-item-label>
          <q-item clickable v-ripple :to="'/users'">
            <q-item-section avatar><q-icon name="manage_accounts" color="red-7" /></q-item-section>
            <q-item-section>Utilizadores</q-item-section>
          </q-item>
          <q-item clickable v-ripple :to="'/login-logs'">
            <q-item-section avatar><q-icon name="history" color="blue-grey-6" /></q-item-section>
            <q-item-section>Registo de Acessos</q-item-section>
          </q-item>
          <q-item clickable v-ripple :to="'/backup'">
            <q-item-section avatar><q-icon name="cloud_upload" color="teal-6" /></q-item-section>
            <q-item-section>Cópia de Segurança</q-item-section>
          </q-item>
        </template>

        <q-separator />
        <q-item clickable v-ripple :to="'/app-settings'">
          <q-item-section avatar><q-icon name="notifications" color="teal-7" /></q-item-section>
          <q-item-section>Configurações</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/about'">
          <q-item-section avatar><q-icon name="info" color="blue-5" /></q-item-section>
          <q-item-section>Sobre</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>

    <AiChatWidget />
  </q-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'
import AiChatWidget from 'components/AiChatWidget.vue'

const appVersion = process.env.APP_VERSION ?? '?'
const leftDrawerOpen = ref(false)
const auth = useAuthStore()
const router = useRouter()
const $q = useQuasar()

const savedDark = localStorage.getItem('darkMode')
if (savedDark !== null) $q.dark.set(savedDark === 'true')

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}

function saveDarkMode() {
  localStorage.setItem('darkMode', String($q.dark.isActive))
}
</script>
