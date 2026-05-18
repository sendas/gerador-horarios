<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />
        <q-toolbar-title>
          <q-icon name="schedule" class="q-mr-sm" />
          Gerador de Horários
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered>
      <q-list>
        <q-item-label header>Navegação</q-item-label>

        <q-item clickable v-ripple :to="'/'">
          <q-item-section avatar><q-icon name="home" /></q-item-section>
          <q-item-section>Dashboard</q-item-section>
        </q-item>

        <q-separator />
        <q-item-label header caption>Configuração</q-item-label>

        <q-item clickable v-ripple :to="'/clusters'">
          <q-item-section avatar><q-icon name="domain" /></q-item-section>
          <q-item-section>Agrupamentos</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/schools'">
          <q-item-section avatar><q-icon name="school" /></q-item-section>
          <q-item-section>Escolas</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/academic-years'">
          <q-item-section avatar><q-icon name="calendar_today" /></q-item-section>
          <q-item-section>Anos Letivos</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/time-slots'">
          <q-item-section avatar><q-icon name="schedule" /></q-item-section>
          <q-item-section>Tempos Letivos</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/rooms'">
          <q-item-section avatar><q-icon name="meeting_room" /></q-item-section>
          <q-item-section>Salas</q-item-section>
        </q-item>

        <q-separator />
        <q-item-label header caption>Curriculum</q-item-label>

        <q-item clickable v-ripple :to="'/subjects'">
          <q-item-section avatar><q-icon name="book" /></q-item-section>
          <q-item-section>Disciplinas</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/classes'">
          <q-item-section avatar><q-icon name="group" /></q-item-section>
          <q-item-section>Turmas</q-item-section>
        </q-item>

        <q-separator />
        <q-item-label header caption>Pessoal</q-item-label>

        <q-item clickable v-ripple :to="'/teachers'">
          <q-item-section avatar><q-icon name="person" /></q-item-section>
          <q-item-section>Professores</q-item-section>
        </q-item>

        <q-item clickable v-ripple :to="'/non-teaching'">
          <q-item-section avatar><q-icon name="work_off" /></q-item-section>
          <q-item-section>Serviço Não Letivo</q-item-section>
        </q-item>

        <q-separator />
        <q-item-label header caption>Horários</q-item-label>

        <q-item clickable v-ripple :to="'/timetables'">
          <q-item-section avatar><q-icon name="table_chart" /></q-item-section>
          <q-item-section>Horários</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const leftDrawerOpen = ref(false)

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}
</script>
