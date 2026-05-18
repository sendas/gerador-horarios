<template>
  <q-page padding>
    <div class="row justify-center">
      <div style="max-width: 700px; width: 100%">
        <div class="text-center q-mb-lg">
          <q-icon name="schedule" size="64px" color="primary" />
          <div class="text-h4 q-mt-sm">Gerador de Horários</div>
          <q-badge color="primary" class="q-mt-sm text-subtitle2">v1.2.0</q-badge>
          <div class="text-caption text-grey-6 q-mt-xs">Sistema de geração automática de horários escolares</div>
        </div>

        <q-card flat bordered class="q-mb-md">
          <q-card-section>
            <div class="text-h6 q-mb-md">
              <q-icon name="history" class="q-mr-sm" />Historial de versões
            </div>

            <q-timeline color="primary">
              <q-timeline-entry
                title="v1.2.0 — Importação e Modo Escuro"
                subtitle="Maio 2026"
                icon="auto_awesome"
                color="purple"
              >
                <ul class="q-mb-none q-pl-md">
                  <li>Importação de professores, turmas e salas via CSV/Excel</li>
                  <li>Importação via imagem com IA (Claude Vision)</li>
                  <li>Modo escuro com persistência de preferência</li>
                  <li>Página Sobre com historial de versões</li>
                </ul>
              </q-timeline-entry>

              <q-timeline-entry
                title="v1.1.0 — Autenticação"
                subtitle="Maio 2026"
                icon="lock"
                color="orange"
              >
                <ul class="q-mb-none q-pl-md">
                  <li>Sistema de login JWT com sessões de 8 horas</li>
                  <li>Papéis: Administrador, Utilizador, Visualizador</li>
                  <li>Gestão de utilizadores (admin)</li>
                  <li>Proteção de todas as rotas</li>
                </ul>
              </q-timeline-entry>

              <q-timeline-entry
                title="v1.0.0 — Versão Inicial"
                subtitle="Maio 2026"
                icon="rocket_launch"
                color="positive"
              >
                <ul class="q-mb-none q-pl-md">
                  <li>Gestão de agrupamentos, escolas e anos letivos</li>
                  <li>Configuração de tempos letivos por escola</li>
                  <li>Salas, disciplinas, turmas e currículo</li>
                  <li>Professores — escolas, disciplinas, disponibilidade</li>
                  <li>Geração automática de horários com OR-Tools</li>
                  <li>Exportação HTML, CSV e Excel</li>
                  <li>Grupos de disciplinas (coadjuvação, desdobramento)</li>
                </ul>
              </q-timeline-entry>
            </q-timeline>
          </q-card-section>
        </q-card>

        <q-card flat bordered class="q-mb-md">
          <q-card-section>
            <div class="text-h6 q-mb-sm">
              <q-icon name="build" class="q-mr-sm" />Tecnologias
            </div>
            <div class="row q-gutter-sm">
              <q-chip icon="memory" color="blue" text-color="white">FastAPI</q-chip>
              <q-chip icon="storage" color="brown" text-color="white">SQLite</q-chip>
              <q-chip icon="calculate" color="green" text-color="white">OR-Tools CP-SAT</q-chip>
              <q-chip icon="code" color="teal" text-color="white">Vue 3</q-chip>
              <q-chip icon="palette" color="primary" text-color="white">Quasar</q-chip>
              <q-chip icon="auto_awesome" color="purple" text-color="white">Claude AI</q-chip>
              <q-chip icon="inventory_2" color="orange" text-color="white">Docker</q-chip>
            </div>
          </q-card-section>
        </q-card>

        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6 q-mb-sm">
              <q-icon name="description" class="q-mr-sm" />Formatos de importação
            </div>
            <p class="text-body2 q-mb-sm">Os ficheiros CSV e Excel devem conter os seguintes campos:</p>
            <q-list bordered separator dense>
              <q-item>
                <q-item-section avatar><q-icon name="person" color="primary" /></q-item-section>
                <q-item-section>
                  <q-item-label><strong>Professores:</strong> <code>nome</code>, <code>email</code> (opcional), <code>max_aulas_dia</code> (opcional)</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar><q-icon name="group" color="secondary" /></q-item-section>
                <q-item-section>
                  <q-item-label><strong>Turmas:</strong> <code>nome</code>, <code>ano</code> (opcional), <code>alunos</code> (opcional)</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar><q-icon name="meeting_room" color="positive" /></q-item-section>
                <q-item-section>
                  <q-item-label><strong>Salas:</strong> <code>nome</code>, <code>capacidade</code> (opcional), <code>tipo</code> (opcional)</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
</script>
