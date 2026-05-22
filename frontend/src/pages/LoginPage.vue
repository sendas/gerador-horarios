<template>
  <div class="login-root">

    <!-- Dark mode toggle -->
    <div class="dark-toggle">
      <q-btn flat round :icon="$q.dark.isActive ? 'light_mode' : 'dark_mode'"
        :color="$q.dark.isActive ? 'yellow-5' : 'blue-2'" @click="toggleDark">
        <q-tooltip>{{ $q.dark.isActive ? 'Modo claro' : 'Modo escuro' }}</q-tooltip>
      </q-btn>
    </div>

    <!-- Floating decorative blobs -->
    <div class="blob blob-1" />
    <div class="blob blob-2" />
    <div class="blob blob-3" />

    <div class="login-layout">

      <!-- ── Left panel: branding ─────────────────────────────────────── -->
      <div class="brand-panel">
        <div class="brand-inner">

          <div class="brand-logo">
            <q-icon name="hub" size="54px" color="white" />
          </div>

          <div class="brand-title">Sinaptik</div>
          <div class="brand-tagline">
            Plataforma inteligente de horários escolares.<br>
            <span class="tagline-accent">O sistema mais completo para criação automática de horários para agrupamentos escolares</span>
            — define professores, disciplinas, restrições e obtém horários otimizados em minutos.
          </div>

          <div class="feature-list">
            <div class="feature-item">
              <span class="feature-dot dot-blue" />
              <span>Geração automática com IA</span>
            </div>
            <div class="feature-item">
              <span class="feature-dot dot-green" />
              <span>Restrições totalmente configuráveis</span>
            </div>
            <div class="feature-item">
              <span class="feature-dot dot-orange" />
              <span>Múltiplas escolas e agrupamentos</span>
            </div>
            <div class="feature-item">
              <span class="feature-dot dot-purple" />
              <span>Disponibilidade e preferências por professor</span>
            </div>
            <div class="feature-item">
              <span class="feature-dot dot-teal" />
              <span>Visualização e exportação de horários</span>
            </div>
          </div>

          <div class="brand-version">v{{ appVersion }}</div>
        </div>
      </div>

      <!-- ── Right panel: form ──────────────────────────────────────────── -->
      <div class="form-panel">
        <div class="form-card">

          <div class="form-header">
            <div class="form-title">Bem-vindo</div>
            <div class="form-subtitle">Inicie sessão para continuar</div>
          </div>

          <q-form @submit.prevent="handleLogin" class="form-body">
            <q-input
              v-model="username"
              label="Utilizador"
              outlined dense
              autofocus
              :disable="loading"
              :rules="[(v) => !!v || 'Obrigatório']"
              class="form-input"
            >
              <template #prepend><q-icon name="person" color="primary" /></template>
            </q-input>

            <q-input
              v-model="password"
              label="Palavra-passe"
              outlined dense
              :type="showPassword ? 'text' : 'password'"
              :disable="loading"
              :rules="[(v) => !!v || 'Obrigatória']"
              class="form-input"
            >
              <template #prepend><q-icon name="lock" color="primary" /></template>
              <template #append>
                <q-icon :name="showPassword ? 'visibility_off' : 'visibility'"
                  class="cursor-pointer" color="grey-6"
                  @click="showPassword = !showPassword" />
              </template>
            </q-input>

            <q-banner v-if="errorMsg" dense rounded class="bg-red-1 text-red-9 q-mb-sm">
              <template #avatar><q-icon name="error" color="negative" /></template>
              {{ errorMsg }}
            </q-banner>

            <q-btn type="submit" color="primary" label="Entrar"
              class="full-width login-btn" size="md" unelevated :loading="loading">
              <template #loading>
                <q-spinner-dots color="white" />
              </template>
            </q-btn>
          </q-form>

          <div class="demo-section">
            <div class="demo-divider">
              <span class="demo-divider-line" />
              <span class="demo-divider-text">ou</span>
              <span class="demo-divider-line" />
            </div>
            <q-btn outline color="teal" icon="explore" label="Explorar Demo"
              class="full-width" :loading="demoLoading" @click="handleDemo" />
            <div class="demo-hint">Explore sem conta — dados de demonstração</div>
          </div>

        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'

const appVersion = process.env.APP_VERSION ?? '?'

const router = useRouter()
const auth = useAuthStore()
const $q = useQuasar()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const demoLoading = ref(false)
const errorMsg = ref('')

const savedDark = localStorage.getItem('darkMode')
if (savedDark !== null) $q.dark.set(savedDark === 'true')

function toggleDark() {
  $q.dark.toggle()
  localStorage.setItem('darkMode', String($q.dark.isActive))
}

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    await router.push('/')
  } catch {
    errorMsg.value = 'Utilizador ou palavra-passe incorretos'
  } finally {
    loading.value = false
  }
}

async function handleDemo() {
  errorMsg.value = ''
  demoLoading.value = true
  try {
    await auth.demoLogin()
    await router.push('/')
  } catch {
    errorMsg.value = 'Modo demo não disponível de momento'
  } finally {
    demoLoading.value = false
  }
}
</script>

<style scoped>
/* ── Root ──────────────────────────────────────────────────────────────────── */
.login-root {
  min-height: 100vh;
  display: flex;
  align-items: stretch;
  position: relative;
  overflow: hidden;
  background: #f0f4f8;
}
.body--dark .login-root {
  background: #0d1117;
}

/* ── Floating blobs ────────────────────────────────────────────────────────── */
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
  pointer-events: none;
  animation: drift 18s ease-in-out infinite alternate;
}
.blob-1 {
  width: 520px; height: 520px;
  background: radial-gradient(circle, #1565c0, #42a5f5);
  top: -160px; left: -120px;
  animation-duration: 20s;
}
.blob-2 {
  width: 380px; height: 380px;
  background: radial-gradient(circle, #6a1b9a, #ab47bc);
  bottom: -100px; left: 30%;
  animation-duration: 15s;
  animation-delay: -6s;
}
.blob-3 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, #00695c, #26c6da);
  top: 40%; right: -80px;
  animation-duration: 22s;
  animation-delay: -10s;
}
@keyframes drift {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(30px, 20px) scale(1.08); }
}
.body--dark .blob { opacity: 0.18; }

/* ── Layout ────────────────────────────────────────────────────────────────── */
.dark-toggle {
  position: absolute;
  top: 14px; right: 14px;
  z-index: 10;
}

.login-layout {
  display: flex;
  width: 100%;
  position: relative;
  z-index: 2;
}

/* ── Brand panel (left) ────────────────────────────────────────────────────── */
.brand-panel {
  flex: 1.1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
  background: linear-gradient(150deg, #0d47a1 0%, #1565c0 45%, #0277bd 100%);
  position: relative;
  overflow: hidden;
}
.body--dark .brand-panel {
  background: linear-gradient(150deg, #0a0f1e 0%, #0d1f3c 50%, #0a1929 100%);
}

.brand-inner {
  max-width: 380px;
  color: white;
}

.brand-logo {
  width: 80px; height: 80px;
  border-radius: 22px;
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  border: 1px solid rgba(255,255,255,0.25);
}

.brand-title {
  font-size: 2.6rem;
  font-weight: 800;
  letter-spacing: -1.5px;
  line-height: 1;
  margin-bottom: 16px;
}

.brand-tagline {
  font-size: 1.05rem;
  line-height: 1.65;
  opacity: 0.9;
  margin-bottom: 40px;
  font-weight: 300;
}
.tagline-accent {
  font-weight: 700;
  color: #80d8ff;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 48px;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.92rem;
  opacity: 0.9;
}
.feature-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-blue   { background: #40c4ff; box-shadow: 0 0 8px #40c4ff88; }
.dot-green  { background: #69f0ae; box-shadow: 0 0 8px #69f0ae88; }
.dot-orange { background: #ffab40; box-shadow: 0 0 8px #ffab4088; }
.dot-purple { background: #e040fb; box-shadow: 0 0 8px #e040fb88; }
.dot-teal   { background: #64ffda; box-shadow: 0 0 8px #64ffda88; }

.brand-version {
  font-size: 0.75rem;
  opacity: 0.45;
  letter-spacing: 1px;
  font-family: monospace;
}

/* ── Form panel (right) ────────────────────────────────────────────────────── */
.form-panel {
  flex: 0.9;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 32px;
}

.form-card {
  width: 100%;
  max-width: 380px;
  background: white;
  border-radius: 20px;
  padding: 40px 36px;
  box-shadow: 0 8px 48px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.05);
}
.body--dark .form-card {
  background: #161b22;
  box-shadow: 0 8px 48px rgba(0,0,0,0.4), 0 1px 4px rgba(0,0,0,0.2);
  border: 1px solid rgba(255,255,255,0.06);
}

.form-header {
  margin-bottom: 28px;
}
.form-title {
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: #1a237e;
  margin-bottom: 4px;
}
.body--dark .form-title { color: #90caf9; }
.form-subtitle {
  font-size: 0.88rem;
  color: #78909c;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-input {
  margin-bottom: 4px;
}

.login-btn {
  margin-top: 8px;
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 0.3px;
  height: 44px;
}

.demo-section {
  margin-top: 20px;
}
.demo-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.demo-divider-line {
  flex: 1;
  height: 1px;
  background: #e0e0e0;
}
.body--dark .demo-divider-line { background: rgba(255,255,255,0.1); }
.demo-divider-text {
  font-size: 0.78rem;
  color: #9e9e9e;
}
.demo-hint {
  text-align: center;
  font-size: 0.75rem;
  color: #9e9e9e;
  margin-top: 8px;
}

/* ── Responsive: single column on mobile ──────────────────────────────────── */
@media (max-width: 700px) {
  .login-layout { flex-direction: column; }

  .brand-panel {
    flex: none;
    padding: 40px 24px 32px;
  }
  .brand-inner { max-width: 100%; text-align: center; }
  .brand-logo { margin: 0 auto 20px; }
  .brand-title { font-size: 2rem; }
  .brand-tagline { font-size: 1rem; margin-bottom: 24px; }
  .feature-list { display: none; }

  .form-panel {
    flex: none;
    padding: 28px 20px 40px;
    background: #f0f4f8;
  }
  .body--dark .form-panel { background: #0d1117; }
}
</style>
