# Sinaptik — Manual de Utilizador
**Versão 1.7.0 · Maio 2026**

---

## Índice

1. [Introdução](#1-introdução)
2. [Acesso e Autenticação](#2-acesso-e-autenticação)
3. [Conceitos Base](#3-conceitos-base)
4. [Configuração Inicial (passo a passo)](#4-configuração-inicial-passo-a-passo)
5. [Gestão de Escolas e Agrupamentos](#5-gestão-de-escolas-e-agrupamentos)
6. [Anos Letivos e Horários de Aulas](#6-anos-letivos-e-horários-de-aulas)
7. [Professores](#7-professores)
8. [Turmas e Currículos](#8-turmas-e-currículos)
9. [Disciplinas](#9-disciplinas)
10. [Salas](#10-salas)
11. [Regras de Geração](#11-regras-de-geração)
12. [Serviço Não Letivo](#12-serviço-não-letivo)
13. [Gerar Horário](#13-gerar-horário)
14. [Visualizar e Editar o Horário](#14-visualizar-e-editar-o-horário)
15. [Exportar Horários](#15-exportar-horários)
16. [Importações em Massa](#16-importações-em-massa)
17. [Cópias de Segurança](#17-cópias-de-segurança)
18. [Gestão de Utilizadores](#18-gestão-de-utilizadores)
19. [Modo Demonstração](#19-modo-demonstração)
20. [Resolução de Problemas](#20-resolução-de-problemas)
21. [Referência Rápida](#21-referência-rápida)

---

## 1. Introdução

O **Sinaptik** é uma plataforma de geração automática de horários escolares. Usa o solver CP-SAT (OR-Tools da Google) para encontrar horários que satisfaçam simultaneamente todas as restrições configuradas — sem sobreposições de professores, sem furos nos alunos, com os blocos consecutivos nas posições certas.

### O que o Sinaptik faz

- Gera horários para turmas do 5.º ao 12.º ano.
- Respeita a disponibilidade semanal e as preferências de cada professor.
- Distribui disciplinas de forma equilibrada ao longo da semana.
- Suporta disciplinas semestrais em alternância (ex.: TIC ↔ Educação Musical).
- Suporta desdobramentos e turnos de laboratório (ex.: CN + FQ em simultâneo, turmas divididas).
- Permite edição manual com deteção de conflitos em tempo real.

### O que o Sinaptik não faz (ainda)

- Não gera horários de exames.
- Não gera horários de substituições automáticas.
- Não calcula componente não letiva automaticamente (tem de ser introduzida manualmente).

---

## 2. Acesso e Autenticação

### Login

Aceda ao Sinaptik pelo browser. Na página de login:

| Campo | Descrição |
|---|---|
| Utilizador | Nome de utilizador atribuído pelo administrador |
| Palavra-passe | Palavra-passe pessoal |

A sessão dura **8 horas**. Após esse período será pedido novo login.

### Níveis de acesso

| Papel | Permissões |
|---|---|
| **Admin** | Acesso total, incluindo gestão de utilizadores |
| **Utilizador** | Acesso total exceto gestão de utilizadores |
| **Visualizador** | Apenas leitura (sem criar, editar ou apagar) |

### Explorar sem conta

Clique em **"Explorar Demo"** para aceder ao modo de demonstração sem criar conta. Os dados do modo demo são só de leitura e partilhados.

---

## 3. Conceitos Base

Antes de começar, é importante conhecer a hierarquia de dados do Sinaptik:

```
Agrupamento
  └─ Escola
       └─ Ano Letivo
            ├─ Tempos (horário da escola: slots do dia)
            ├─ Professores (afetos ao agrupamento)
            ├─ Turmas
            │    └─ Currículo (disciplinas + horas semanais)
            ├─ Regras de Geração
            └─ Horário(s) gerado(s)
```

**Agrupamento**: A entidade de topo. Normalmente corresponde a um agrupamento de escolas (ex.: "Agrupamento de Escolas da Amora").

**Escola**: Uma escola dentro do agrupamento (ex.: EB2/3 da Amora, ES Amora). Professores podem lecionar em mais do que uma escola.

**Ano Letivo**: Ex.: "2025/2026". Cada ano letivo pertence a um agrupamento. Só pode estar **um** ativo de cada vez.

**Tempos**: A grelha de horas do dia para uma escola — ex.: Tempo 1 (8h20–9h05), Tempo 2 (9h10–9h55), etc.

**Currículo**: A lista de disciplinas de uma turma com o número de horas semanais de cada uma.

**Horário**: O resultado da geração — a atribuição de cada aula a um dia/tempo específico.

---

## 4. Configuração Inicial (passo a passo)

Siga esta ordem na primeira utilização:

### Passo 1 — Criar o Agrupamento

**Menu: Agrupamentos**

1. Clique em **"Novo Agrupamento"**.
2. Preencha o nome (ex.: "Agrupamento de Escolas X") e uma descrição opcional.
3. Confirme com **"Guardar"**.

### Passo 2 — Criar as Escolas

**Menu: Escolas**

1. Clique em **"Nova Escola"**.
2. Preencha nome, código, morada e selecione o agrupamento.
3. Repita para cada escola (sede, básicas, etc.).

### Passo 3 — Criar o Ano Letivo

**Menu: Anos Letivos**

1. Clique em **"Novo Ano Letivo"**.
2. Preencha o nome (ex.: "2025/2026"), datas de início e fim, e selecione o agrupamento.
3. Marque como **ativo** se for o corrente.

### Passo 4 — Configurar os Tempos

**Menu: Tempos**

Defina os tempos letivos para cada escola e para cada dia da semana:

1. Selecione o ano letivo e a escola.
2. Selecione o dia da semana.
3. Clique em **"Adicionar Tempo"** e preencha:
   - Número do tempo (1, 2, 3, …)
   - Hora de início e fim
   - Assinale **"Intervalo/Almoço"** no tempo que corresponde ao almoço.
4. Repita para todos os dias.

> **Dica:** Se todos os dias tiverem a mesma estrutura, crie para segunda e depois edite os restantes.

### Passo 5 — Criar as Disciplinas

**Menu: Disciplinas**

Crie todas as disciplinas do agrupamento (ver secção [9. Disciplinas](#9-disciplinas) para detalhes).

### Passo 6 — Criar as Salas (opcional)

**Menu: Salas**

Se quiser atribuir salas nos horários, crie-as aqui.

### Passo 7 — Criar os Professores

**Menu: Professores**

Crie os professores e configure disponibilidade e disciplinas (ver secção [7. Professores](#7-professores)).

### Passo 8 — Criar as Turmas e Currículos

**Menu: Turmas**

Crie as turmas e para cada turma defina o currículo (ver secção [8. Turmas e Currículos](#8-turmas-e-currículos)).

### Passo 9 — Configurar as Regras

**Menu: Regras de Geração**

Ajuste as restrições do solver antes de gerar (ver secção [11. Regras de Geração](#11-regras-de-geração)).

### Passo 10 — Gerar o Horário

**Menu: Horários**

Crie um horário e clique em Gerar (ver secção [13. Gerar Horário](#13-gerar-horário)).

---

## 5. Gestão de Escolas e Agrupamentos

### Agrupamentos (`/clusters`)

- Cada agrupamento é uma entidade autónoma com os seus próprios professores, turmas e horários.
- Numa instalação de escola única, crie apenas um agrupamento.

### Escolas (`/schools`)

- As escolas pertencem a um agrupamento.
- Um professor pode ser atribuído a várias escolas, com um **tempo de deslocação** configurável (em minutos) — o solver garante que não há aulas consecutivas em escolas com tempo de deslocação incompatível.

---

## 6. Anos Letivos e Horários de Aulas

### Anos Letivos (`/anos-letivos`)

- Só um ano letivo pode estar **ativo** por agrupamento em simultâneo.
- Os dados de turmas, currículos e professores ficam associados ao ano letivo.
- Para iniciar um novo ano, crie um novo ano letivo e migre os dados (ou use importação).

### Tempos (`/time-slots`)

Os tempos definem a grelha do dia:

| Campo | Descrição |
|---|---|
| Número do tempo | Posição sequencial (1 = primeiro tempo do dia) |
| Hora de início | Hora de início do tempo |
| Hora de fim | Hora de fim do tempo |
| Intervalo/Almoço | Marcar se este tempo corresponde ao almoço |

> **Importante:** O tempo marcado como almoço é usado pela regra "Educação Física nunca depois do almoço" e pela opção "Alunos entram no 1.º tempo".

---

## 7. Professores

**Menu: Professores**

### Criar um Professor

1. Clique em **"Novo Professor"**.
2. Preencha:
   - **Nome** e **Email** (opcional)
   - **Máx. aulas/dia**: limite de tempos letivos por dia (ex.: 6)
   - **Dia livre preferido**: dia da semana em que o professor prefere não ter aulas
   - **Tempo de início mínimo**: o professor não quer começar antes deste tempo (ex.: 2 = não começa no 1.º tempo)
   - **Tempo de fim máximo**: o professor não quer acabar depois deste tempo
   - **Turno preferido**: manhã ou tarde
   - **Máx. aulas consecutivas**: substitui a regra global para este professor

### Atribuir Escolas

Na linha do professor, clique em **"Escolas"**:
- Adicione as escolas onde leciona.
- Para cada escola, defina o **tempo de deslocação** (minutos necessários para chegar entre escolas).

### Atribuir Disciplinas

Na linha do professor, clique em **"Disciplinas"**:
- Selecione as disciplinas que o professor pode lecionar.
- A atribuição a turmas específicas faz-se no currículo de cada turma.

### Configurar Disponibilidade

Na linha do professor, clique em **"Disponibilidade"**:
- Uma grelha semanal (dias × tempos) é apresentada.
- Clique nas células para marcar como **disponível** (verde) ou **indisponível** (vermelho).
- Por defeito todos os tempos estão disponíveis.

> **Nota:** Indisponibilidade é uma restrição rígida — o solver nunca coloca uma aula nesse slot.

### Importar Professores

Clique em **"Importar"** e carregue um ficheiro CSV ou Excel com colunas:

```
nome, email (opcional), max_aulas_dia (opcional)
```

---

## 8. Turmas e Currículos

**Menu: Turmas**

### Criar uma Turma

1. Clique em **"Nova Turma"**.
2. Preencha nome (ex.: "8.ºA"), ano de escolaridade, n.º de alunos, escola e ano letivo.

### Editar o Currículo

Na linha da turma, clique em **"Currículo"** (ícone de livro).

O currículo define **que disciplinas** a turma tem e **quantas horas por semana**.

#### Adicionar uma entrada ao currículo

1. Selecione a disciplina e o professor.
2. Defina as horas semanais.
3. Configure a estrutura semanal conforme necessário (ver abaixo).
4. Clique em **"Adicionar"**.

#### Estrutura semanal (tempos)

Cada disciplina pode ter uma das seguintes estruturas:

| Estrutura | Significado |
|---|---|
| `1` | Um tempo por semana |
| `1+1` | Dois tempos separados (um por dia diferente) |
| `2` | Um bloco de dois tempos consecutivos |
| `2+1` | Um bloco de dois + um tempo separado |
| `1+1+1` | Três tempos em dias diferentes |

Para configurar blocos:
- Ative **"Dividir em blocos"** e defina o número de blocos.
- Para blocos consecutivos, defina **"Pares consecutivos"** (ex.: 1 par = o bloco de 2 deve estar em tempos consecutivos).

#### Disciplinas semestrais

Para disciplinas que apenas funcionam num semestre:
1. Ative **"Semestral"**.
2. Selecione o semestre (1.º ou 2.º).
3. Opcionalmente, selecione a **disciplina par** — a disciplina que ocupa o mesmo slot no semestre oposto (ex.: TIC no 1.º semestre, EM no 2.º). A associação é bidirecional.

#### Turnos (desdobramento por grupos)

Para disciplinas como CN e FQ que partilham professores e laboratórios em turnos:

1. Na secção **"Turnos (Grupos de Disciplinas Simultâneas)"**, clique em **"Novo Turno"**.
2. Dê um nome ao turno (ex.: "Turnos Lab CN/FQ").
3. Clique em **"+"** para adicionar as entradas do currículo que compõem o turno (ex.: a entrada de CN e a entrada de FQ).
4. O solver permite que as entradas do mesmo turno ocorram no **mesmo slot em simultâneo** (cada grupo de alunos com o seu professor).

### Importar Currículo Completo

Clique em **"Importar Currículo"** e carregue um ficheiro CSV/Excel com colunas:

```
ano, turma, disciplina, horas_semana, professor, articulado (opcional)
```

---

## 9. Disciplinas

**Menu: Disciplinas**

### Criar uma Disciplina

| Campo | Descrição |
|---|---|
| Nome | Nome completo (ex.: "Ciências Naturais") |
| Código | Abreviatura (ex.: "CN") |
| Cor | Cor de destaque na grelha do horário |
| Estrutura semanal | Configuração padrão de tempos (1, 1+1, 2, 2+1, 1+1+1) |
| Regime | Anual ou Semestral |
| Semestre padrão | Para disciplinas semestrais: em que semestre leciona por defeito |
| Educação Física | Marcar se for EF — sujeita à regra "sem EF depois do almoço" |
| Pode isentar articulado | Marcar se pode ser dispensada em ensino articulado |

A **cor** é escolhida de uma paleta de 15 cores. Cada disciplina deve ter uma cor distinta para facilitar a leitura dos horários.

---

## 10. Salas

**Menu: Salas**

### Criar uma Sala

| Campo | Descrição |
|---|---|
| Nome | Ex.: "Sala 101", "Laboratório de Física" |
| Capacidade | N.º máximo de alunos |
| Tipo | Ex.: "Normal", "Laboratório", "Ginásio" |
| Escola | Escola a que pertence |

> **Nota atual:** A atribuição automática de salas na geração ainda não está implementada. As salas são reservadas para edição manual na grelha.

---

## 11. Regras de Geração

**Menu: Regras de Geração**

As regras são configuradas por **agrupamento e ano letivo** e são usadas automaticamente na geração.

### Limites de tempos

| Regra | Descrição |
|---|---|
| Máx. tempos/dia (turma) | Máximo de tempos letivos por dia por turma |
| Máx. tempos/dia (professor) | Máximo de tempos letivos por dia por professor |
| Máx. consecutivos (turma) | Máximo de tempos seguidos sem intervalo para turmas |
| Máx. consecutivos (professor) | Máximo de tempos seguidos sem intervalo para professores |

### Restrições dos alunos

| Regra | Tipo | Descrição |
|---|---|---|
| Sem furos nos horários dos alunos | Rígida | Os alunos nunca têm tempos livres no meio do dia |
| Alunos entram sempre no 1.º tempo | Rígida | O dia letivo dos alunos começa sempre no tempo 1 |
| Educação Física nunca depois do almoço | Rígida | EF é marcada antes do tempo de almoço |
| Tempo do almoço | Configuração | Número do tempo que corresponde ao almoço (ex.: 4) |

### Preferências dos professores

| Regra | Tipo | Descrição |
|---|---|---|
| Minimizar furos nos horários dos professores | Suave | O solver tenta reduzir tempos livres entre aulas |
| Peso dos furos (professores) | Peso | Quanto o solver penaliza cada furo (1–50) |

### Distribuição de disciplinas

| Regra | Tipo | Descrição |
|---|---|---|
| Máx. 1 tempo por disciplina por dia | Suave | Evita a mesma disciplina duas vezes no mesmo dia |
| Distribuir disciplinas ao longo da semana | Suave | Espalha as aulas de cada disciplina |
| Peso da distribuição | Peso | Intensidade da preferência de distribuição (0–10) |

> **Restrições rígidas** são sempre satisfeitas (o solver recusa soluções que as violem).
> **Restrições suaves** são preferências — o solver tenta satisfazê-las mas pode ignorá-las se necessário.

---

## 12. Serviço Não Letivo

**Menu: Serviço Não Letivo**

Permite registar os tempos de serviço não letivo de cada professor (direção de turma, reuniões, vigilâncias, etc.).

### Tipos de serviço

1. Clique em **"Novo Tipo"** (painel esquerdo).
2. Dê um nome (ex.: "Direção de Turma") e escolha uma cor.

### Atribuir serviço a um professor

1. No painel direito, selecione o professor e o ano letivo.
2. Clique em **"Novo Serviço"**.
3. Selecione o tipo, o dia e o tempo.

> **Nota:** O serviço não letivo bloqueia esse slot para o professor — o solver não marca aulas nesses tempos.

---

## 13. Gerar Horário

**Menu: Horários**

### Criar um Horário

1. Clique em **"Novo Horário"**.
2. Selecione o ano letivo e dê um nome (ex.: "Horário 2025/2026 v1").
3. Confirme. O horário fica no estado **Rascunho**.

### Iniciar a Geração

1. Na linha do horário, clique em **"Gerar"**.
2. Configura as opções de geração:

#### Ciclos a incluir

Selecione quais os ciclos a incluir na geração:
- 2.º Ciclo (5.º–6.º ano)
- 3.º Ciclo (7.º–9.º ano)
- Secundário (10.º–12.º ano)

#### Opções de geração

| Opção | Tipo | Descrição |
|---|---|---|
| Sem furos nos horários dos alunos | Rígida | Substitui a regra global para esta geração |
| Alunos entram sempre no 1.º tempo | Rígida | Substitui a regra global para esta geração |
| Educação Física nunca depois do almoço | Rígida | Substitui a regra global para esta geração |
| Minimizar furos (professores) | Suave | Ativa a penalização de furos |
| Peso dos furos | Peso | Ajustável com slider (1–50) |
| Máx. 1 tempo por disciplina por dia | Suave | Limita a uma aula por disciplina por dia |
| Distribuir disciplinas ao longo da semana | Suave | Melhora distribuição semanal |
| Tempo máximo de cálculo | Limite | 1 min / 2 min / 5 min / 10 min |

3. Clique em **"Gerar Horário"**. A geração corre **em segundo plano**.

### Estados do Horário

| Estado | Significado |
|---|---|
| Rascunho | Criado mas não gerado |
| A gerar | Geração em curso |
| Gerado | Geração concluída com sucesso |
| Erro | A geração falhou |

> **Dica:** Se o estado ficar em "Erro", verifique se todas as turmas têm currículo completo com professores atribuídos e se os professores têm as disciplinas corretamente configuradas.

### Tempo de cálculo recomendado

| Situação | Tempo recomendado |
|---|---|
| Escola pequena (< 10 turmas) | 1–2 min |
| Escola média (10–20 turmas) | 2–5 min |
| Escola grande (> 20 turmas) | 5–10 min |
| Muitas restrições rígidas | 5–10 min |

---

## 14. Visualizar e Editar o Horário

**Menu: Horários → Ver**

### Modos de visualização

Use o seletor no topo para escolher a perspetiva:

| Modo | Mostra |
|---|---|
| **Por Turma** | Horário de uma turma específica |
| **Por Professor** | Horário de um professor específico |
| **Por Sala** | Ocupação de uma sala específica |

Selecione a entidade pretendida no segundo seletor.

### Leitura da grelha

- As **colunas** representam os dias da semana (Segunda–Sexta).
- As **linhas** representam os tempos letivos.
- Cada célula mostra: **disciplina** (com cor), **turma** (ou professor, consoante o modo) e **sala** (se atribuída).

### Edição manual (arrastar e largar)

Para mover uma aula:
1. Clique e segure na aula que quer mover.
2. Arraste para o slot de destino.
3. O slot de destino fica **verde** se estiver livre, **laranja** se houver conflito.
4. Se houver conflito, uma caixa de diálogo pergunta se quer forçar a mudança.

> **Conflitos detetados:** sobreposição de professor, sobreposição de turma, sobreposição de sala (quando atribuída).

---

## 15. Exportar Horários

Na página de visualização do horário, use os botões de exportação:

| Formato | Uso recomendado |
|---|---|
| **HTML** | Publicar no site da escola ou partilhar por email |
| **Excel** | Edição adicional em folha de cálculo |
| **CSV** | Importação para outros sistemas |
| **PDF** | Impressão física |

O PDF abre a caixa de diálogo de impressão do browser — selecione "Guardar como PDF" para guardar o ficheiro.

---

## 16. Importações em Massa

Para poupar tempo na configuração inicial, use as funcionalidades de importação.

### Formato dos ficheiros

Todos os ficheiros podem ser **CSV** (separador vírgula) ou **Excel** (.xlsx).
A primeira linha deve ser o cabeçalho.

### Professores

```
nome, email, max_aulas_dia
João Silva, joao@escola.pt, 6
Maria Santos, , 5
```

### Turmas

```
nome, ano, alunos
8.ºA, 8, 28
8.ºB, 8, 27
9.ºA, 9, 25
```

### Salas

```
nome, capacidade, tipo
Sala 101, 30, Normal
Lab. Física, 24, Laboratório
Ginásio, 60, Ginásio
```

### Currículo Completo

```
ano, turma, disciplina, horas_semana, professor, articulado
8, 8.ºA, Português, 5, Maria Silva, 0
8, 8.ºA, Matemática, 5, João Santos, 0
8, 8.ºA, Ciências Naturais, 3, Ana Costa, 0
```

### Importação por imagem (IA)

Na importação de currículo, pode **fotografar uma tabela** de horário ou currículo existente. O sistema usa visão computacional (Claude AI) para extrair os dados automaticamente.

> **Nota:** A qualidade do reconhecimento depende da nitidez da imagem e da clareza do formato da tabela.

---

## 17. Cópias de Segurança

**Menu: Backup**

### Backup local

1. Clique em **"Fazer Backup (Download)"**.
2. Um ficheiro `.sqlite` é descarregado para o seu computador.
3. Guarde-o num local seguro.

### Restauro

1. Em caso de necessidade, contacte o administrador do sistema.
2. O restauro faz-se através da opção **"Restaurar Backup"** na mesma página.

### Backup automático para OneDrive

Para configurar backups automáticos na nuvem:

1. Clique em **"Configurar OneDrive"**.
2. Introduza o **Client ID** da aplicação Azure (ver instruções no ecrã).
3. Clique em **"Iniciar Autorização"**.
4. Abra o URL indicado no browser, introduza o código apresentado e aceite as permissões.
5. O sistema aguarda confirmação e guarda as credenciais.

Após configurado, escolha a **frequência** de backup automático:
- Manual (apenas quando clicar)
- Diário
- Semanal
- Mensal

O histórico de backups mostra data, destino, tamanho e estado de cada operação.

---

## 18. Gestão de Utilizadores

**Menu: Utilizadores** (visível apenas para Administradores)

### Criar um Utilizador

1. Clique em **"Novo Utilizador"**.
2. Preencha:
   - **Nome de utilizador**: usado no login (sem espaços)
   - **Nome completo**: nome para apresentação
   - **Palavra-passe**: mínimo 6 caracteres
   - **Papel**: Admin / Utilizador / Visualizador

### Editar um Utilizador

- Altere nome completo, papel ou estado (ativo/inativo).
- Um utilizador inativo não consegue fazer login.

### Repor Palavra-passe

- Clique em **"Repor Password"** e introduza a nova palavra-passe.
- Não é necessário saber a palavra-passe atual.

> **Nota:** Não é possível apagar ou desativar a própria conta.

---

## 19. Modo Demonstração

O modo demonstração inclui dados pré-configurados:

- 1 Agrupamento, 1 Escola
- 1 Ano Letivo ativo
- 7 Turmas (5.º ao 9.º ano)
- 10 Disciplinas com cores distintas
- 6 Professores com disponibilidades
- 1 Horário gerado e pronto a explorar

Para aceder: clique em **"Explorar Demo"** na página de login.

> **Atenção:** As alterações feitas no modo demo são **perdidas** quando o servidor reiniciar. O modo demo destina-se apenas à exploração das funcionalidades.

---

## 20. Resolução de Problemas

### A geração termina com estado "Erro"

**Causas mais comuns:**
1. **Turma sem currículo**: Certifique-se que todas as turmas selecionadas têm entradas no currículo com professor atribuído.
2. **Professor sem disponibilidade**: Verifique se os professores têm slots disponíveis suficientes para as suas aulas.
3. **Demasiadas restrições rígidas conflituantes**: Experimente desativar algumas restrições rígidas (ex.: "sem furos" + "entrar no 1.º tempo" em conjunto podem ser impossíveis com certos currículos).
4. **Disciplinas com blocos consecutivos**: Se a disciplina tem blocos consecutivos e também a regra "máx. 1 tempo por disciplina por dia" estava ativa numa versão anterior — esta combinação foi corrigida na v1.7.0.

**Solução:** Verifique os dados, reduza restrições, aumente o tempo de cálculo e tente novamente.

### A geração demora muito sem resultado

- Aumente o tempo máximo de cálculo (10 min para horários complexos).
- Reduza o número de ciclos a gerar de uma vez.
- Remova algumas restrições suaves (distribuição, furos de professores) para simplificar o modelo.

### O horário gerado tem muitos furos nos professores

- Ative **"Minimizar furos nos horários dos professores"** e aumente o peso (20–50).
- Gere novamente com mais tempo disponível.

### Não consigo arrastar aulas para certos slots

- O slot pode estar bloqueado por uma restrição rígida (disponibilidade do professor, sobreposição).
- Use a opção de **forçar** a mudança se tiver certeza que é válida manualmente.

### Esqueci a palavra-passe

- Contacte o administrador do sistema para repor a palavra-passe (Menu Utilizadores → Repor Password).

### Como atualizar o sistema

```bash
# No servidor onde está instalado:
cd /caminho/para/gerador-horarios
git pull origin main
docker compose up -d --build
```

---

## 21. Referência Rápida

### Atalhos de configuração inicial

| O que fazer | Onde |
|---|---|
| Criar agrupamento | Menu → Agrupamentos |
| Criar escola | Menu → Escolas |
| Criar ano letivo | Menu → Anos Letivos |
| Configurar tempos do dia | Menu → Tempos |
| Criar disciplinas | Menu → Disciplinas |
| Criar professores | Menu → Professores |
| Atribuir disciplinas a professores | Professores → Disciplinas |
| Configurar disponibilidade | Professores → Disponibilidade |
| Criar turmas | Menu → Turmas |
| Definir currículo | Turmas → Currículo |
| Configurar regras | Menu → Regras de Geração |

### Fluxo de geração

```
Criar Horário → Gerar → Aguardar → Visualizar → (Editar manualmente) → Exportar
```

### Estados dos horários

| Ícone/Cor | Estado | Ação recomendada |
|---|---|---|
| Cinzento | Rascunho | Clique em "Gerar" |
| Amarelo/animado | A gerar | Aguarde |
| Verde | Gerado | Clique em "Ver" |
| Vermelho | Erro | Verifique dados e tente novamente |

---

*Manual de utilizador do Sinaptik v1.7.0 · Maio 2026*
*Desenvolvido por sendas · Assistência IA: Claude (Anthropic)*
