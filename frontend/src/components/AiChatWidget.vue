<template>
  <!-- Floating button -->
  <q-btn
    fab
    icon="smart_toy"
    color="primary"
    class="fixed"
    style="bottom: 24px; right: 24px; z-index: 1200"
    @click="open = true"
  >
    <q-tooltip>Assistente IA</q-tooltip>
    <q-badge v-if="unread > 0" color="red" floating>{{ unread }}</q-badge>
  </q-btn>

  <!-- Chat panel -->
  <q-dialog v-model="open" position="right" :maximized="$q.screen.lt.sm" @show="onOpen">
    <q-card
      flat
      style="width: 420px; max-width: 100vw; height: 100vh; display: flex; flex-direction: column; border-radius: 0"
    >
      <!-- Header -->
      <q-card-section class="row items-center q-py-sm" :class="$q.dark.isActive ? 'bg-blue-grey-9' : 'bg-primary'">
        <q-icon name="smart_toy" color="white" class="q-mr-sm" size="sm" />
        <span class="text-subtitle1 text-weight-medium text-white">Assistente Sinaptik</span>
        <q-space />
        <q-btn flat round dense icon="delete_outline" color="white" @click="clearChat">
          <q-tooltip>Limpar conversa</q-tooltip>
        </q-btn>
        <q-btn flat round dense icon="close" color="white" v-close-popup />
      </q-card-section>

      <!-- API key warning -->
      <q-banner
        v-if="apiKeyMissing"
        :class="$q.dark.isActive ? 'bg-orange-9' : 'bg-orange-1'"
        dense
      >
        <template #avatar><q-icon name="warning" color="orange" /></template>
        <span class="text-caption">
          <strong>ANTHROPIC_API_KEY</strong> não configurada.<br>
          Adiciona ao <code>docker-compose.yml</code> em <code>environment:</code>.
        </span>
      </q-banner>

      <!-- Messages -->
      <q-scroll-area ref="scrollRef" style="flex: 1" class="q-px-sm q-pt-sm">
        <!-- Welcome -->
        <div v-if="messages.length === 0" class="text-center q-py-xl">
          <q-icon name="smart_toy" size="48px" :color="$q.dark.isActive ? 'blue-3' : 'primary'" class="q-mb-sm" />
          <div class="text-subtitle2 q-mb-xs">Olá! Como posso ajudar?</div>
          <div class="text-caption text-grey-6 q-mb-lg">Pergunta em linguagem natural sobre professores, horários ou distribuição de serviço.</div>

          <!-- Suggestion chips -->
          <div class="row wrap justify-center q-gutter-sm">
            <q-chip
              v-for="s in suggestions"
              :key="s"
              clickable
              size="sm"
              :color="$q.dark.isActive ? 'blue-grey-7' : 'blue-1'"
              :text-color="$q.dark.isActive ? 'white' : 'primary'"
              @click="sendSuggestion(s)"
            >
              {{ s }}
            </q-chip>
          </div>
        </div>

        <!-- Message list -->
        <div v-for="(msg, i) in messages" :key="i" class="q-mb-sm">
          <!-- User message -->
          <div v-if="msg.role === 'user'" class="row justify-end">
            <div
              class="q-pa-sm q-px-md rounded-borders text-body2"
              style="max-width: 80%; word-break: break-word"
              :class="$q.dark.isActive ? 'bg-blue-grey-7' : 'bg-primary text-white'"
            >
              {{ msg.content }}
            </div>
          </div>

          <!-- Assistant message -->
          <div v-else class="row items-start q-gutter-xs">
            <q-avatar size="28px" :color="$q.dark.isActive ? 'blue-grey-7' : 'blue-1'" class="q-mt-xs flex-shrink-0">
              <q-icon name="smart_toy" :color="$q.dark.isActive ? 'blue-3' : 'primary'" size="16px" />
            </q-avatar>
            <div style="flex: 1; min-width: 0">
              <!-- Tool badges -->
              <div v-if="msg.tools_called && msg.tools_called.length" class="q-mb-xs row q-gutter-xs">
                <q-chip
                  v-for="tool in uniqueTools(msg.tools_called)"
                  :key="tool"
                  dense size="xs"
                  :color="$q.dark.isActive ? 'indigo-9' : 'indigo-1'"
                  :text-color="$q.dark.isActive ? 'indigo-2' : 'indigo-8'"
                  icon="build"
                >
                  {{ toolLabel(tool) }}
                </q-chip>
              </div>
              <!-- Content -->
              <div
                class="q-pa-sm q-px-md rounded-borders text-body2"
                :class="[
                  msg.error
                    ? ($q.dark.isActive ? 'bg-red-9' : 'bg-red-1 text-negative')
                    : ($q.dark.isActive ? 'bg-blue-grey-8' : 'bg-grey-2'),
                ]"
                style="word-break: break-word"
                v-html="renderMarkdown(msg.content)"
              />
            </div>
          </div>
        </div>

        <!-- Typing indicator -->
        <div v-if="loading" class="row items-start q-gutter-xs q-mb-sm">
          <q-avatar size="28px" :color="$q.dark.isActive ? 'blue-grey-7' : 'blue-1'">
            <q-icon name="smart_toy" :color="$q.dark.isActive ? 'blue-3' : 'primary'" size="16px" />
          </q-avatar>
          <div
            class="q-pa-sm q-px-md rounded-borders"
            :class="$q.dark.isActive ? 'bg-blue-grey-8' : 'bg-grey-2'"
          >
            <div class="row items-center q-gutter-xs">
              <span class="text-caption text-grey-6">{{ loadingLabel }}</span>
              <q-spinner-dots color="grey-5" size="18px" />
            </div>
          </div>
        </div>
      </q-scroll-area>

      <!-- Input -->
      <q-separator />
      <q-card-section class="q-pa-sm">
        <div class="row items-end q-gutter-xs">
          <q-input
            v-model="input"
            outlined dense autogrow
            placeholder="Escreve aqui…"
            style="flex: 1"
            :disable="loading"
            @keydown.enter.exact.prevent="send"
          />
          <q-btn
            round flat
            icon="send"
            color="primary"
            size="md"
            :loading="loading"
            :disable="!input.trim()"
            @click="send"
          />
        </div>
        <div class="text-caption text-grey-5 q-mt-xs text-right">Enter para enviar</div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, nextTick, computed } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAcademicYearsStore } from 'stores/academicYears'

const $q = useQuasar()
const yearsStore = useAcademicYearsStore()

// ── State ─────────────────────────────────────────────────────────────────────

interface Message {
  role: 'user' | 'assistant'
  content: string
  tools_called?: string[]
  error?: boolean
}

const open = ref(false)
const input = ref('')
const loading = ref(false)
const loadingLabel = ref('A pensar…')
const messages = ref<Message[]>([])
const unread = ref(0)
const apiKeyMissing = ref(false)
const scrollRef = ref<{ setScrollPercentage: (axis: string, pct: number) => void } | null>(null)

const suggestions = [
  'Consigo gerar o horário agora?',
  'Mostra o horário da turma 8A',
  'Quais professores estão em défice de horas?',
  'Gera o horário para o 7.º e 8.º ano',
  'Define 22h letivas a todos com Art. 79.°',
]

// ── Tool labels ───────────────────────────────────────────────────────────────

const TOOL_LABELS: Record<string, string> = {
  obter_contexto: 'contexto',
  listar_professores: 'professores',
  atualizar_professor: 'atualizar prof.',
  listar_turmas: 'turmas',
  ver_estado_horario: 'estado horário',
  ver_preflight_horario: 'preflight',
  criar_horario: 'criar horário',
  iniciar_geracao: 'gerar horário',
  ver_horario_professor: 'horário prof.',
  ver_horario_turma: 'horário turma',
  mover_aula: 'mover aula',
  ver_distribuicao_servico: 'distribuição',
  definir_componentes_letivos: 'componentes',
  listar_servico_nao_letivo: 'serv. não letivo',
  ver_regras_horario: 'regras',
}

function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? name
}

function uniqueTools(tools: string[]): string[] {
  return [...new Set(tools)]
}

// ── Markdown renderer ─────────────────────────────────────────────────────────

function renderMarkdown(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(128,128,128,.15);padding:1px 4px;border-radius:3px">$1</code>')
    .replace(/^### (.+)$/gm, '<strong class="text-subtitle2">$1</strong>')
    .replace(/^## (.+)$/gm, '<strong class="text-subtitle1">$1</strong>')
    .replace(/^# (.+)$/gm, '<strong class="text-h6">$1</strong>')
    .replace(/^- (.+)$/gm, '• $1')
    .replace(/\n/g, '<br>')
}

// ── Scroll to bottom ──────────────────────────────────────────────────────────

async function scrollToBottom() {
  await nextTick()
  scrollRef.value?.setScrollPercentage('vertical', 1.0)
}

// ── Chat logic ────────────────────────────────────────────────────────────────

function onOpen() {
  unread.value = 0
  scrollToBottom()
}

function clearChat() {
  messages.value = []
  apiKeyMissing.value = false
}

function sendSuggestion(text: string) {
  input.value = text
  send()
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  loadingLabel.value = 'A pensar…'
  await scrollToBottom()

  // Build conversation history for API (only role + content text)
  const history = messages.value
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .map((m) => ({ role: m.role, content: m.content }))

  // Context hints
  const activeYear = yearsStore.years.find((y) => y.is_active)

  try {
    const { data } = await api.post('/ai/chat', {
      messages: history,
      academic_year_id: activeYear?.id ?? null,
      cluster_id: activeYear?.cluster_id ?? null,
    })

    // Simulate a slight delay before showing tool info
    if (data.tools_called?.length) {
      loadingLabel.value = `A usar ${data.tools_called.length} ferramenta(s)…`
      await new Promise((r) => setTimeout(r, 300))
    }

    messages.value.push({
      role: 'assistant',
      content: data.response,
      tools_called: data.tools_called ?? [],
    })
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string }; status?: number } }
    const detail = err.response?.data?.detail ?? 'Erro de comunicação com o servidor.'
    if (err.response?.status === 503) {
      apiKeyMissing.value = true
    }
    messages.value.push({ role: 'assistant', content: detail, error: true })
  } finally {
    loading.value = false
    if (!open.value) unread.value++
    await scrollToBottom()
  }
}
</script>
