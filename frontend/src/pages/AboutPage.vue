<template>
  <q-page>
    <!-- Hero banner -->
    <div class="hero">
      <div class="hero__icon-wrap">
        <q-icon name="hub" size="48px" color="white" />
      </div>
      <div class="hero__title">Sinaptik</div>
      <q-badge class="hero__badge">v{{ appVersion }}</q-badge>
      <div class="hero__subtitle">
        Plataforma Inteligente de Horários — o sistema mais completo para criação automática de horários para agrupamentos escolares
      </div>
    </div>

    <!-- Page body -->
    <div class="q-pa-md">
      <div class="row justify-center">
        <div style="max-width: 780px; width: 100%">

          <!-- Version history -->
          <div class="section-label">
            <q-icon name="tag" size="xs" class="q-mr-xs" />Historial de versões
          </div>

          <q-timeline color="primary" layout="comfortable" class="q-mt-xs">

            <q-timeline-entry icon="schedule" color="indigo-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="indigo-8" class="version-badge">v1.23.0</q-badge>
                  Correção de fórmulas Art.79° e TE/TIA
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />23 de maio de 2026, 14:00
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="elderly" size="xs" color="indigo-8" />
                  <strong>Art. 79° ECD corrigido</strong>: escalões 50–54a → 2h · 55–59a → 4h · ≥60a → 6h (em vez de 1/2/3h)
                </div>
                <div class="feature-item">
                  <q-icon name="calculate" size="xs" color="indigo-8" />
                  <strong>Fórmula correta</strong>: CL líq. = CL − Art.79° · TE líq. = (TE_base + Art.79°) − Crédito H. · TIA = 35 − CL líq. − TE líq.
                </div>
                <div class="feature-item">
                  <q-icon name="card_membership" size="xs" color="indigo-8" />
                  <strong>Crédito H. reduz TE</strong> (não a CL) — horas de art.79° transferem-se de CL para TE
                </div>
                <div class="feature-item">
                  <q-icon name="list" size="xs" color="indigo-8" />
                  <strong>Alocações TE itemizadas</strong>: cada atividade/cargo tem o seu número de horas editável
                </div>
                <div class="feature-item">
                  <q-icon name="cancel" size="xs" color="indigo-8" />
                  Botão para <strong>limpar data de nascimento</strong> de cada docente
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="schedule" color="teal-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="teal-8" class="version-badge">v1.22.0</q-badge>
                  Definição de Horas por Docente — CL / TE / TIA
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />23 de maio de 2026, 09:30
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="calculate" size="xs" color="teal-8" />
                  Novo diálogo <strong>Componentes</strong> em Distribuição de Serviço com estrutura completa das 35h: CL · TE · TIA · Red. Art.79° · Crédito H. · CL líquida
                </div>
                <div class="feature-item">
                  <q-icon name="business" size="xs" color="teal-8" />
                  <strong>TE</strong> (Trabalho no Estabelecimento, base 3h) com campo de cargo atribuível — reuniões de avaliação, coordenação pedagógica, apoio educativo, etc.
                </div>
                <div class="feature-item">
                  <q-icon name="home" size="xs" color="teal-8" />
                  <strong>TIA</strong> (Trabalho Individual Autónomo) calculado automaticamente: 35 − CL − TE (ex: 22h CL → 3h TE → 10h TIA)
                </div>
                <div class="feature-item">
                  <q-icon name="filter_list" size="xs" color="teal-8" />
                  Filtro por escola na página de distribuição + botões de aplicação em massa CL=22h (2.º/3.º ciclo) e CL=25h (1.º ciclo)
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="expand_more" color="indigo-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="indigo-8" class="version-badge">v1.21.0</q-badge>
                  Expansão de Professor, Navegação e Correção do Chat IA
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />22 de maio de 2026, 23:00
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="expand_more" size="xs" color="indigo-8" />
                  Na página <strong>Professores</strong>, clicar no nome expande uma linha inline com as escolas atribuídas (escola base em destaque) e as turmas do docente para o ano letivo ativo
                </div>
                <div class="feature-item">
                  <q-icon name="schedule" size="xs" color="indigo-8" />
                  Menu <strong>Pessoal</strong>: "Distribuição de Serviço" passou a <strong>Definição de horas por docente</strong> (inclui componente letiva, data de nascimento e reduções Art. 79°)
                </div>
                <div class="feature-item">
                  <q-icon name="smart_toy" size="xs" color="indigo-8" />
                  Chat IA: mensagem de erro do Gemini passa a mostrar o detalhe real da quota em vez de mensagem genérica fixa
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="build" color="deep-purple-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="deep-purple-7" class="version-badge">v1.20.0</q-badge>
                  Atribuição de Professores — Correções e Melhorias
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />22 de maio de 2026, 21:05
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="sync" size="xs" color="deep-purple-7" />
                  Botão <strong>Sincronizar disciplinas</strong> sem preencher automaticamente — aplica o plano curricular à turma sem sobrepor atribuições existentes
                </div>
                <div class="feature-item">
                  <q-icon name="notifications_off" size="xs" color="deep-purple-7" />
                  Corrigida notificação de erro ao sincronizar que mostrava <em>[object Object]</em> em vez de mensagem legível
                </div>
                <div class="feature-item">
                  <q-icon name="block" size="xs" color="deep-purple-7" />
                  Corrigida gravação de blocos indisponíveis na página de Professores (problema de reatividade Vue 3 com Map)
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="analytics" color="teal-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="teal-7" class="version-badge">v1.19.0</q-badge>
                  Distribuição de Serviço — Saldo de Horas em Tempo Real
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />22 de maio de 2026, 20:22
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="analytics" size="xs" color="teal-7" />
                  Painel <strong>Saldo de Horas Letivas</strong> sempre visível ao atribuir professores: mostra todos os docentes ordenados por horas livres, com barra de progresso e estado a cores (completo / incompleto / excedido). Atualiza em tempo real à medida que as atribuições são feitas
                </div>
                <div class="feature-item">
                  <q-icon name="badge" size="xs" color="teal-7" />
                  Nos <em>dropdowns</em> de professor, cada opção mostra as horas livres do docente — facilita escolher quem ainda tem capacidade disponível
                </div>
                <div class="feature-item">
                  <q-icon name="auto_fix_high" size="xs" color="teal-7" />
                  "Preencher auto" melhorado: escolhe o professor com mais horas disponíveis em vez de aleatório, ajudando a equilibrar o serviço automaticamente
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="sync" color="orange-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="orange-8" class="version-badge">v1.18.0</q-badge>
                  Sincronização do Plano Curricular + Filtros de Turmas
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />22 de maio de 2026, 15:46
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="sync" size="xs" color="orange-8" />
                  Novo botão <strong>Sincronizar das turmas</strong> em Planos Curriculares: preenche o plano com base nas disciplinas já atribuídas às turmas (inverso do "Aplicar às turmas") — resolve o desfasamento entre plano e currículo real das turmas
                </div>
                <div class="feature-item">
                  <q-icon name="filter_list" size="xs" color="orange-8" />
                  Em <strong>Turmas</strong>, novos filtros rápidos por escola e por ano de escolaridade para encontrar turmas facilmente em agrupamentos grandes
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="call_split" color="secondary">
              <template #title>
                <span class="version-title">
                  <q-badge color="secondary" class="version-badge">v1.17.0</q-badge>
                  Separação clara entre Currículo e Turnos
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />22 de maio de 2026, 15:25
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="menu_book" size="xs" color="secondary" />
                  <strong>Planos Curriculares</strong> é agora a única fonte de verdade para definir, editar e remover disciplinas das turmas
                </div>
                <div class="feature-item">
                  <q-icon name="call_split" size="xs" color="secondary" />
                  Em <strong>Turmas</strong>, o botão "Currículo" passou a "Turnos" — gere apenas grupos de disciplinas simultâneas (turnos). O currículo da turma é visível em modo de leitura com ligação direta aos Planos Curriculares
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="group" color="indigo-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="indigo-7" class="version-badge">v1.16.0</q-badge>
                  Contagem Correta de Professores no Solver
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />22 de maio de 2026, 14:05
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="bug_report" size="xs" color="indigo-7" />
                  O solver carregava todos os professores da base de dados em vez de apenas os relevantes para as turmas selecionadas — o log mostrava 115 professores para a VG quando eram muito menos
                </div>
                <div class="feature-item">
                  <q-icon name="speed" size="xs" color="indigo-7" />
                  Melhoria de desempenho: variáveis de soft constraints (turnos preferidos, dias livres, aulas diárias) agora criadas apenas para os professores com ocorrências no âmbito da geração
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="build" color="red-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="red-8" class="version-badge">v1.15.0</q-badge>
                  Correções Críticas no Motor de Geração
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />22 de maio de 2026, 11:23
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="bug_report" size="xs" color="red-8" />
                  Correção crítica: geração falhava com erro "(eid, occ, slot)" quando professores tinham blocos de disponibilidade configurados — o solver apresentava o erro como status em vez de gerar o horário
                </div>
                <div class="feature-item">
                  <q-icon name="timer" size="xs" color="red-8" />
                  Fase 3 (retry automático sem restrições rígidas) recebe agora até 50% do tempo original (máx. 30 min) em vez dos 7 min anteriores
                </div>
                <div class="feature-item">
                  <q-icon name="warning" size="xs" color="orange-8" />
                  Aviso de complexidade no log quando há muitos professores com poucas aulas — informa que "sem furos" fica muito difícil nesse cenário
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="auto_awesome" color="teal-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="teal-7" class="version-badge">v1.14.0</q-badge>
                  Blocos Indisponíveis, Solver Otimizado e Melhorias Visuais
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />22 de maio de 2026, 08:47
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="event_busy" size="xs" color="teal-7" />
                  Blocos indisponíveis: substituída seleção de dia por grelha visual interativa — clique para bloquear/desbloquear slots por dia e tempo, aplica a todos os docentes
                </div>
                <div class="feature-item">
                  <q-icon name="timer" size="xs" color="teal-7" />
                  Geração de horários: novos tempos máximos de cálculo — 30 min, 1h, 2h, 3h, 5h, 10h
                </div>
                <div class="feature-item">
                  <q-icon name="calculate" size="xs" color="teal-7" />
                  Solver CP-SAT: penalização O(n) por blocos não consecutivos (substituiu O(n³)), AllDifferent + AtMostOne para dupla propagação, parâmetros de Fase 1/2 otimizados
                </div>
                <div class="feature-item">
                  <q-icon name="warning" size="xs" color="orange-8" />
                  Aviso visível na página de horários quando a Fase 3 removeu restrições (ex: "sem furos") para obter solução
                </div>
                <div class="feature-item">
                  <q-icon name="login" size="xs" color="teal-7" />
                  Página de login redesenhada: painel duplo, blobs animados, lista de funcionalidades colorida e versão dinâmica
                </div>
                <div class="feature-item">
                  <q-icon name="bug_report" size="xs" color="red-7" />
                  Correção: blocos indisponíveis não eram guardados (problema de reatividade Vue 3 com Set dentro de ref)
                </div>
                <div class="feature-item">
                  <q-icon name="build" size="xs" color="teal-7" />
                  Versão centralizada no package.json — atualiza automaticamente em todos os ecrãs da aplicação
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="analytics" color="orange-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="orange-8" class="version-badge">v1.10.8</q-badge>
                  Diagnósticos de Geração e Melhorias nos Tempos Letivos
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 19:30
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="bug_report" size="xs" color="orange-8" />
                  Log de geração mostra carga por turma, avisos de sobrecarga e professores com disponibilidade insuficiente — antes de chamar o solver
                </div>
                <div class="feature-item">
                  <q-icon name="content_copy" size="xs" color="orange-8" />
                  Tempos letivos: botão "Replicar para outros dias" — copia os tempos de um dia para os restantes dias da semana de uma vez
                </div>
                <div class="feature-item">
                  <q-icon name="content_copy" size="xs" color="orange-8" />
                  Tempos letivos: "Copiar de..." agora disponível para os tempos globais (sem escola) — permite copiar tempos de uma escola para o reserva global
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="build" color="red-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="red-8" class="version-badge">v1.10.7</q-badge>
                  Correção do Motor de Geração — Tempos Letivos por Escola
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 18:30
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="schedule" size="xs" color="red-8" />
                  O motor de geração agora usa os tempos letivos específicos de cada escola (se configurados), em vez de misturar todas as escolas — elimina o erro "INFEASIBLE" causado por configurações de tempos conflituantes
                </div>
                <div class="feature-item">
                  <q-icon name="warning" size="xs" color="red-8" />
                  Validação prévia da configuração de tempos: erro claro e descritivo quando os tempos são insuficientes (em vez de INFEASIBLE do solver)
                </div>
                <div class="feature-item">
                  <q-icon name="info" size="xs" color="red-8" />
                  Log de geração mostra agora quais tempos letivos foram usados por escola e distribuição por dia
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="tune" color="deep-purple-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="deep-purple-8" class="version-badge">v1.10.6</q-badge>
                  Geração por Escola, Ano e Turmas Individuais
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 18:00
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="school" size="xs" color="deep-purple-8" />
                  Seleção de escolas no diálogo de geração — gera apenas as turmas das escolas selecionadas
                </div>
                <div class="feature-item">
                  <q-icon name="filter_list" size="xs" color="deep-purple-8" />
                  Filtro por ano de escolaridade com chips dinâmicos (baseados nas turmas existentes)
                </div>
                <div class="feature-item">
                  <q-icon name="group" size="xs" color="deep-purple-8" />
                  Seleção de turmas individuais (expandível) — combina com os filtros de escola e ano
                </div>
                <div class="feature-item">
                  <q-icon name="info" size="xs" color="deep-purple-8" />
                  Resumo em tempo real das turmas incluídas na geração
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="auto_fix_high" color="indigo-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="indigo-7" class="version-badge">v1.10.5</q-badge>
                  Preenchimento e Limpeza Automática de Professores por Turma
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 13:00
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="auto_fix_high" size="xs" color="indigo-7" />
                  Botão "Preencher auto" na Atribuição de Professores por Turma — atribui aleatoriamente um professor qualificado a cada disciplina sem professor
                </div>
                <div class="feature-item">
                  <q-icon name="filter_list" size="xs" color="indigo-7" />
                  Opções de âmbito: todos visíveis, por ano de escolaridade (seleção por chips), ou apenas turmas selecionadas
                </div>
                <div class="feature-item">
                  <q-icon name="person_remove" size="xs" color="indigo-7" />
                  Botão "Limpar" para remover todos os professores — de todas as turmas visíveis ou apenas das selecionadas
                </div>
                <div class="feature-item">
                  <q-icon name="checklist" size="xs" color="indigo-7" />
                  Checkboxes na lista de turmas para multi-seleção, com "Selecionar todos" e "Limpar seleção"
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="checklist" color="teal-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="teal-7" class="version-badge">v1.10.4</q-badge>
                  Seleção de Anos para Geração na Verificação de Dados
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 12:00
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="fact_check" size="xs" color="teal-7" />
                  A verificação antes de gerar mostra agora o estado de cada ano de escolaridade (viável/não viável) com contagem de entradas com e sem professor
                </div>
                <div class="feature-item">
                  <q-icon name="checklist" size="xs" color="teal-7" />
                  Permite selecionar individualmente quais os anos de escolaridade a incluir na geração — pré-seleciona automaticamente os viáveis
                </div>
                <div class="feature-item">
                  <q-icon name="play_arrow" size="xs" color="teal-7" />
                  Botão "Gerar selecionados" diretamente na janela de verificação, com seletor do horário a usar
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="bug_report" color="pink-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="pink-8" class="version-badge">v1.10.3</q-badge>
                  Correção: Atribuição de Escola ao Professor
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 11:35
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="school" size="xs" color="pink-8" />
                  Corrigido erro que impedia guardar a escola de um professor — o schema de criação passou a aceitar teacher_id como opcional (vinha no URL, não no body)
                </div>
                <div class="feature-item">
                  <q-icon name="notifications" size="xs" color="pink-8" />
                  Notificações de sucesso e erro ao adicionar/remover escola de um professor
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="warning" color="orange-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="orange-8" class="version-badge">v1.10.2</q-badge>
                  Deteção de Geração Interrompida
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 11:22
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="error" size="xs" color="orange-8" />
                  Banner de aviso vermelho quando a geração para sem terminar — detectado por ausência de heartbeat durante mais de 3 minutos
                </div>
                <div class="feature-item">
                  <q-icon name="cancel" size="xs" color="orange-8" />
                  Botão "Cancelar" para marcar manualmente uma geração presa como falhada
                </div>
                <div class="feature-item">
                  <q-icon name="restart_alt" size="xs" color="orange-8" />
                  Ao arrancar, o servidor marca automaticamente como erro qualquer horário que ficou preso em "a gerar" (ex: após reinício do Docker)
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="bug_report" color="teal-8">
              <template #title>
                <span class="version-title">
                  <q-badge color="teal-8" class="version-badge">v1.10.1</q-badge>
                  Correções na Atribuição de Turmas
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 10:59
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="groups" size="xs" color="teal-8" />
                  Corrigido erro "Erro ao criar entrada curricular" ao atribuir turmas a um professor — o schema de criação de entradas curriculares passou a aceitar teacher_id diretamente
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="tune" color="blue-9">
              <template #title>
                <span class="version-title">
                  <q-badge color="blue-9" class="version-badge">v1.10.0</q-badge>
                  Atribuição de Turmas, Verificação de Dados e Gestão de Horas
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />20 de maio de 2026, 09:47
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="upload_file" size="xs" color="blue-9" />
                  Página dedicada de importação de currículo com barra de progresso em tempo real (streaming NDJSON)
                </div>
                <div class="feature-item">
                  <q-icon name="save" size="xs" color="blue-9" />
                  Importação resumível: cada linha é confirmada individualmente — se interrompida, retoma do ponto de paragem
                </div>
                <div class="feature-item">
                  <q-icon name="assignment_ind" size="xs" color="blue-9" />
                  Importação de Componente Letiva via CSV: atualiza horas semanais de cada professor
                </div>
                <div class="feature-item">
                  <q-icon name="smart_button" size="xs" color="blue-9" />
                  Botões com texto em toda a aplicação (substituição de ícones sem legenda)
                </div>
                <div class="feature-item">
                  <q-icon name="dark_mode" size="xs" color="blue-9" />
                  Correções de modo escuro: banners, chips, tabelas e fundos em todos os menus
                </div>
                <div class="feature-item">
                  <q-icon name="group" size="xs" color="blue-9" />
                  Página de Atribuição de Professores por Turma: vista centrada na turma, com disciplinas e professores atribuídos, pesquisa por nome, adição e remoção de disciplinas e professores
                </div>
                <div class="feature-item">
                  <q-icon name="fact_check" size="xs" color="blue-9" />
                  Verificação de dados antes de gerar: botão "Verificar dados" com relatório de erros, avisos e informações, com ligações diretas para corrigir cada problema
                </div>
                <div class="feature-item">
                  <q-icon name="schedule" size="xs" color="blue-9" />
                  Visibilidade da geração de horários: banner de progresso, linha pulsante, atualização automática a cada 3 segundos e heartbeat de 60 em 60 segundos no log
                </div>
                <div class="feature-item">
                  <q-icon name="tune" size="xs" color="blue-9" />
                  Gestão de horas na Distribuição de Serviço: definição de horas por escola, seleção múltipla de professores e aplicação de reduções em bloco
                </div>
                <div class="feature-item">
                  <q-icon name="notifications" size="xs" color="blue-9" />
                  Notificações Pushbullet quando a geração de horários termina (sucesso ou erro)
                </div>
                <div class="feature-item">
                  <q-icon name="memory" size="xs" color="blue-9" />
                  Limites de memória Docker e do solver para estabilidade em hardware com recursos limitados
                </div>
                <div class="feature-item">
                  <q-icon name="filter_list" size="xs" color="blue-9" />
                  Filtro de professores por escola na página de Professores
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="dashboard_customize" color="deep-purple-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="deep-purple-7" class="version-badge">v1.9.0</q-badge>
                  Distribuição de Serviço, Log de Geração e Mais
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />19 de maio de 2026, 18:32
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="assignment_ind" size="xs" color="deep-purple-7" />
                  Distribuição de Serviço: vista por professor com turmas, horas letivas e não letivas
                </div>
                <div class="feature-item">
                  <q-icon name="terminal" size="xs" color="deep-purple-7" />
                  Log de geração em tempo real: mostra progresso do solver passo a passo
                </div>
                <div class="feature-item">
                  <q-icon name="work" size="xs" color="deep-purple-7" />
                  Componente letiva por professor: configurar entre 14 e 22 horas/semana
                </div>
                <div class="feature-item">
                  <q-icon name="download" size="xs" color="deep-purple-7" />
                  Exportação corrigida: HTML, Excel, CSV e PDF funcionam com autenticação
                </div>
                <div class="feature-item">
                  <q-icon name="lunch_dining" size="xs" color="deep-purple-7" />
                  Hora de almoço detetada automaticamente dos tempos letivos configurados por escola/ano
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="healing" color="red-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="red-7" class="version-badge">v1.8.0</q-badge>
                  Robustez do Gerador e Manual de Utilizador
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />19 de maio de 2026, 09:30
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="shield" size="xs" color="red-7" />
                  Em caso de erro, o horário existente é preservado (não apagado)
                </div>
                <div class="feature-item">
                  <q-icon name="fact_check" size="xs" color="red-7" />
                  Diagnóstico antes de gerar: lista erros detetados (ex.: disciplinas sem professor)
                </div>
                <div class="feature-item">
                  <q-icon name="auto_fix_high" size="xs" color="red-7" />
                  Auto-ajuste de restrições: mais de turmas do que professores já não bloqueia a geração
                </div>
                <div class="feature-item">
                  <q-icon name="menu_book" size="xs" color="red-7" />
                  Manual de utilizador completo (MANUAL.md)
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="call_split" color="green-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="green-7" class="version-badge">v1.7.0</q-badge>
                  Emparelhamento Semestral &amp; Turnos
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />18 de maio de 2026
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="sync_alt" size="xs" color="green-7" />
                  Emparelhamento semestral bidirecional: TIC ↔ EM no mesmo horário
                </div>
                <div class="feature-item">
                  <q-icon name="call_split" size="xs" color="green-7" />
                  Gestão de turnos: CN e FQ em laboratório em simultâneo (grupos separados)
                </div>
                <div class="feature-item">
                  <q-icon name="auto_fix_high" size="xs" color="green-7" />
                  Correção do gerador: restrição de disciplinas por dia compatível com pares consecutivos
                </div>
                <div class="feature-item">
                  <q-icon name="looks_one" size="xs" color="green-7" />
                  Horário demo reconstruído automaticamente: alunos sempre a entrar no 1.º tempo
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="cloud_upload" color="indigo-6">
              <template #title>
                <span class="version-title">
                  <q-badge color="indigo-6" class="version-badge">v1.6.0</q-badge>
                  Sinaptik — Backup, PDF e Melhorias de UI
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />17 de maio de 2026
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="hub" size="xs" color="indigo-6" />
                  Plataforma renomeada para <strong>Sinaptik</strong> com identidade visual própria
                </div>
                <div class="feature-item">
                  <q-icon name="backup" size="xs" color="indigo-6" />
                  Sistema de backup para OneDrive (OAuth Device Code) e download local
                </div>
                <div class="feature-item">
                  <q-icon name="picture_as_pdf" size="xs" color="indigo-6" />
                  Exportação de horário em PDF (impressão automática no browser)
                </div>
                <div class="feature-item">
                  <q-icon name="view_week" size="xs" color="indigo-6" />
                  Estrutura semanal configurável por disciplina (1, 1+1, 2, 2+1, 1+1+1)
                </div>
                <div class="feature-item">
                  <q-icon name="looks_one" size="xs" color="indigo-6" />
                  Regra: alunos entram sempre no 1.º tempo; EF nunca depois do almoço
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="drag_indicator" color="cyan-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="cyan-7" class="version-badge">v1.5.0</q-badge>
                  Edição Manual — Drag &amp; Drop
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />14 de maio de 2026
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="pan_tool" size="xs" color="cyan-7" />
                  Arrastar e largar aulas na grelha do horário (por turma, professor ou sala)
                </div>
                <div class="feature-item">
                  <q-icon name="warning_amber" size="xs" color="orange-7" />
                  Deteção de incompatibilidades: conflitos de turma e de professor
                </div>
                <div class="feature-item">
                  <q-icon name="palette" size="xs" color="cyan-7" />
                  Feedback visual durante o arrasto — verde (livre) · laranja (conflito)
                </div>
                <div class="feature-item">
                  <q-icon name="bolt" size="xs" color="cyan-7" />
                  Opção de forçar a mudança mesmo com conflitos assinalados
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="tune" color="deep-purple-5">
              <template #title>
                <span class="version-title">
                  <q-badge color="deep-purple-5" class="version-badge">v1.4.0</q-badge>
                  Parametrização Avançada da Geração
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />12 de maio de 2026
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="filter_alt" size="xs" color="deep-purple-5" />
                  Seleção de ciclos: 2.º (5.°-6.°), 3.º (7.°-9.°) e Secundário (10.°-12.°)
                </div>
                <div class="feature-item">
                  <q-icon name="person_pin" size="xs" color="deep-purple-5" />
                  Preferências por professor: turno, hora mín./máx., máx. aulas consecutivas
                </div>
                <div class="feature-item">
                  <q-icon name="block" size="xs" color="deep-purple-5" />
                  Restrição rígida: sem furos nos horários dos alunos
                </div>
                <div class="feature-item">
                  <q-icon name="scatter_plot" size="xs" color="deep-purple-5" />
                  Distribuição inteligente de disciplinas ao longo da semana
                </div>
                <div class="feature-item">
                  <q-icon name="timer" size="xs" color="deep-purple-5" />
                  Tempo limite de cálculo configurável (1, 2, 5 ou 10 minutos)
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="rule" color="blue-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="blue-7" class="version-badge">v1.3.0</q-badge>
                  Regras de Horário e Currículo
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />8 de maio de 2026
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="settings" size="xs" color="blue-7" />
                  Regras de criação de horário configuráveis por agrupamento e ano letivo
                </div>
                <div class="feature-item">
                  <q-icon name="view_week" size="xs" color="blue-7" />
                  Pares consecutivos (ex.: 2 tempos seguidos + 1 isolado por semana)
                </div>
                <div class="feature-item">
                  <q-icon name="calendar_month" size="xs" color="blue-7" />
                  Disciplinas semestrais com emparelhamento automático no horário
                </div>
                <div class="feature-item">
                  <q-icon name="upload_file" size="xs" color="blue-7" />
                  Importação de currículo completo via CSV (turma, disciplina, professor, horas/semana)
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="auto_awesome" color="purple-6">
              <template #title>
                <span class="version-title">
                  <q-badge color="purple-6" class="version-badge">v1.2.0</q-badge>
                  Importações e Modo Escuro
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />5 de maio de 2026
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="table_chart" size="xs" color="purple-6" />
                  Importação de professores, turmas e salas via CSV/Excel
                </div>
                <div class="feature-item">
                  <q-icon name="image_search" size="xs" color="purple-6" />
                  Importação via imagem com IA (Claude Vision)
                </div>
                <div class="feature-item">
                  <q-icon name="dark_mode" size="xs" color="purple-6" />
                  Modo escuro com persistência de preferência
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="lock" color="orange-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="orange-7" class="version-badge">v1.1.0</q-badge>
                  Autenticação e Utilizadores
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />3 de maio de 2026
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="key" size="xs" color="orange-7" />
                  Sistema de login JWT com sessões de 8 horas
                </div>
                <div class="feature-item">
                  <q-icon name="badge" size="xs" color="orange-7" />
                  Papéis: Administrador, Utilizador, Visualizador
                </div>
                <div class="feature-item">
                  <q-icon name="manage_accounts" size="xs" color="orange-7" />
                  Gestão de utilizadores e reposição de palavra-passe
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry icon="rocket_launch" color="teal-7">
              <template #title>
                <span class="version-title">
                  <q-badge color="teal-7" class="version-badge">v1.0.0</q-badge>
                  Versão Inicial
                </span>
              </template>
              <template #subtitle>
                <span class="version-date">
                  <q-icon name="event" size="xs" class="q-mr-xs" />1 de maio de 2026
                </span>
              </template>
              <div class="feature-list">
                <div class="feature-item">
                  <q-icon name="domain" size="xs" color="teal-7" />
                  Agrupamentos, escolas, anos letivos e tempos letivos
                </div>
                <div class="feature-item">
                  <q-icon name="group" size="xs" color="teal-7" />
                  Turmas, disciplinas, professores e currículo
                </div>
                <div class="feature-item">
                  <q-icon name="auto_fix_high" size="xs" color="teal-7" />
                  Geração automática de horários com OR-Tools CP-SAT
                </div>
                <div class="feature-item">
                  <q-icon name="download" size="xs" color="teal-7" />
                  Exportação em HTML, CSV e Excel
                </div>
                <div class="feature-item">
                  <q-icon name="merge" size="xs" color="teal-7" />
                  Grupos de disciplinas (coadjuvação, desdobramento)
                </div>
              </div>
            </q-timeline-entry>

          </q-timeline>

          <!-- Tech stack -->
          <div class="section-label">
            <q-icon name="build" size="xs" class="q-mr-xs" />Tecnologias utilizadas
          </div>
          <div class="row q-col-gutter-sm q-mb-lg">
            <div v-for="tech in techs" :key="tech.name" class="col-6 col-sm-4 col-md-3">
              <q-card flat bordered class="tech-card">
                <q-card-section class="q-pa-sm row items-center no-wrap q-gutter-sm">
                  <q-icon :name="tech.icon" :color="tech.color" size="26px" />
                  <div>
                    <div class="text-weight-bold text-body2">{{ tech.name }}</div>
                    <div class="text-caption text-grey-6">{{ tech.desc }}</div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- Import formats -->
          <div class="section-label">
            <q-icon name="description" size="xs" class="q-mr-xs" />Formatos de importação CSV / Excel
          </div>
          <q-card flat bordered class="q-mb-lg">
            <q-list separator>
              <q-item v-for="fmt in importFormats" :key="fmt.label">
                <q-item-section avatar>
                  <q-icon :name="fmt.icon" :color="fmt.color" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium">{{ fmt.label }}</q-item-label>
                  <q-item-label caption>
                    <template v-for="(field, i) in fmt.fields" :key="field">
                      <code class="field-code">{{ field }}</code>
                      <span v-if="i < fmt.fields.length - 1" class="text-grey-5"> · </span>
                    </template>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Credits -->
          <div class="section-label">
            <q-icon name="favorite" size="xs" class="q-mr-xs" />Créditos e direitos de autor
          </div>
          <q-card flat bordered class="q-mb-lg credits-card">
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="hub" color="primary" size="32px" class="q-mr-md" />
                <div>
                  <div class="text-h6" style="font-weight:700">Sinaptik</div>
                  <div class="text-caption text-grey-6">Plataforma Inteligente de Horários Escolares</div>
                </div>
                <q-space />
                <div class="text-caption text-grey-5">© {{ new Date().getFullYear() }} Todos os direitos reservados</div>
              </div>

              <q-separator class="q-mb-md" />

              <!-- Proprietary notice -->
              <q-banner rounded class="copyright-banner q-mb-md">
                <template #avatar>
                  <q-icon name="gavel" color="blue-9" size="28px" />
                </template>
                <div class="text-body2 text-weight-bold q-mb-xs">
                  O Helpdesk Escolar é propriedade exclusiva de Pedro Sendas de Moura Pereira.
                </div>
                <div class="text-body2">
                  A utilização, reprodução, distribuição, modificação ou qualquer outra forma de exploração deste software — no todo ou em parte — sem autorização escrita prévia do titular dos direitos de autor, é expressamente proibida.
                </div>
              </q-banner>

              <div class="row q-col-gutter-md">
                <div class="col-12 col-sm-6">
                  <div class="text-subtitle2 q-mb-sm">
                    <q-icon name="person" color="blue-7" class="q-mr-xs" />Autor
                  </div>
                  <div class="text-body2 q-mb-xs"><strong>Pedro Sendas de Moura Pereira</strong></div>
                  <div class="text-caption text-grey-6 q-mb-sm">Com o apoio de <strong>Claude AI</strong> (Anthropic) como assistente de desenvolvimento — geração de código, arquitetura e resolução de problemas complexos.</div>
                  <div class="row q-gutter-sm">
                    <q-btn flat size="sm" icon="code" label="GitHub" color="grey-7"
                      href="https://github.com/sendas/gerador-horarios" target="_blank" />
                  </div>
                </div>
                <div class="col-12 col-sm-6">
                  <div class="text-subtitle2 q-mb-sm">
                    <q-icon name="auto_awesome" color="deep-purple-5" class="q-mr-xs" />Desenvolvido com IA
                  </div>
                  <div class="feature-list">
                    <div class="feature-item">
                      <q-icon name="psychology" size="xs" color="deep-purple-5" />
                      Claude (Anthropic) — assistente principal de desenvolvimento
                    </div>
                    <div class="feature-item">
                      <q-icon name="visibility" size="xs" color="blue-6" />
                      Claude Vision — importação de horários por imagem
                    </div>
                    <div class="feature-item">
                      <q-icon name="calculate" size="xs" color="green-7" />
                      OR-Tools CP-SAT (Google) — motor de geração automática
                    </div>
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>

        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
const appVersion = process.env.APP_VERSION ?? '?'

const techs = [
  { name: 'FastAPI', desc: 'API REST', icon: 'bolt', color: 'teal-6' },
  { name: 'SQLite', desc: 'Base de dados', icon: 'storage', color: 'brown-6' },
  { name: 'OR-Tools', desc: 'Solver CP-SAT', icon: 'calculate', color: 'green-7' },
  { name: 'Vue 3', desc: 'Frontend', icon: 'code', color: 'teal-5' },
  { name: 'Quasar', desc: 'UI Framework', icon: 'palette', color: 'blue-6' },
  { name: 'Claude AI', desc: 'IA / Visão', icon: 'auto_awesome', color: 'deep-purple-5' },
  { name: 'Docker', desc: 'Containerização', icon: 'inventory_2', color: 'blue-8' },
  { name: 'TypeScript', desc: 'Tipagem', icon: 'integration_instructions', color: 'indigo-6' },
]

const importFormats = [
  {
    label: 'Currículo Completo',
    icon: 'table_chart',
    color: 'primary',
    fields: ['ano', 'turma', 'disciplina', 'horas semana', 'professor', 'articulado'],
  },
  {
    label: 'Professores',
    icon: 'person',
    color: 'orange-7',
    fields: ['nome', 'email?', 'max_aulas_dia?'],
  },
  {
    label: 'Turmas',
    icon: 'group',
    color: 'secondary',
    fields: ['nome', 'ano?', 'alunos?'],
  },
  {
    label: 'Salas',
    icon: 'meeting_room',
    color: 'positive',
    fields: ['nome', 'capacidade?', 'tipo?'],
  },
]
</script>

<style scoped>
/* ── Hero ─────────────────────────────────────────────────── */
.hero {
  background: linear-gradient(135deg, #1a237e 0%, #283593 25%, #1565c0 60%, #0277bd 100%);
  padding: 52px 24px 44px;
  text-align: center;
  color: #fff;
}

.hero__icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  margin-bottom: 18px;
  backdrop-filter: blur(4px);
}

.hero__title {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin-bottom: 10px;
}

.hero__badge {
  background: rgba(255, 255, 255, 0.25) !important;
  color: #fff !important;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  padding: 4px 12px;
  border-radius: 20px;
  margin-bottom: 14px;
}

.hero__subtitle {
  font-size: 0.95rem;
  opacity: 0.82;
  max-width: 480px;
  margin: 12px auto 0;
  line-height: 1.5;
}

/* ── Section labels ──────────────────────────────────────── */
.section-label {
  display: flex;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #9e9e9e;
  margin-top: 28px;
  margin-bottom: 14px;
}

/* ── Version timeline entries ────────────────────────────── */
.version-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 600;
}

.version-badge {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.3px;
  border-radius: 6px;
  padding: 2px 7px;
}

.version-date {
  font-size: 0.78rem;
  color: #9e9e9e;
  display: flex;
  align-items: center;
  margin-top: 2px;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 6px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 0.82rem;
  line-height: 1.5;
  color: #555;
}

.body--dark .feature-item {
  color: #bbb;
}

/* ── Tech cards ──────────────────────────────────────────── */
.tech-card {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  border-radius: 8px !important;
}

.tech-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1) !important;
}

/* ── Import format codes ─────────────────────────────────── */
.field-code {
  background: rgba(0, 0, 0, 0.06);
  border-radius: 3px;
  padding: 1px 4px;
  font-size: 0.75rem;
  font-family: monospace;
}

.body--dark .field-code {
  background: rgba(255, 255, 255, 0.1);
}

/* ── Credits card ────────────────────────────────────────── */
.credits-card {
  border-radius: 10px !important;
  border-left: 4px solid #1976d2 !important;
}

/* ── Copyright banner ────────────────────────────────────── */
.copyright-banner {
  background: rgba(25, 118, 210, 0.07) !important;
  border: 1px solid rgba(25, 118, 210, 0.25) !important;
  border-radius: 8px !important;
}

.body--dark .copyright-banner {
  background: rgba(25, 118, 210, 0.12) !important;
  border-color: rgba(25, 118, 210, 0.35) !important;
}
</style>
