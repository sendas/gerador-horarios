<template>
  <div
    class="flex flex-center login-bg"
    style="min-height: 100vh; position: relative;"
  >
    <!-- Dark mode toggle top-right -->
    <div style="position: absolute; top: 16px; right: 16px;">
      <q-btn
        flat round
        :icon="$q.dark.isActive ? 'light_mode' : 'dark_mode'"
        :color="$q.dark.isActive ? 'yellow-6' : 'blue-grey-7'"
        @click="toggleDark"
      >
        <q-tooltip>{{ $q.dark.isActive ? 'Modo claro' : 'Modo escuro' }}</q-tooltip>
      </q-btn>
    </div>

    <q-card style="min-width: 360px; max-width: 420px; width: 100%">
      <q-card-section class="bg-primary text-white text-center q-pb-lg">
        <q-icon name="hub" size="52px" />
        <div class="text-h5 q-mt-sm" style="font-weight:700;letter-spacing:-0.5px">Sinaptik</div>
        <div class="text-caption" style="opacity:0.8">Plataforma Inteligente de Horários</div>
      </q-card-section>

      <q-card-section class="q-pt-lg">
        <q-form @submit.prevent="handleLogin" class="q-gutter-md">
          <q-input
            v-model="username"
            label="Utilizador"
            outlined
            autofocus
            :disable="loading"
            :rules="[(v) => !!v || 'Obrigatório']"
          >
            <template #prepend><q-icon name="person" /></template>
          </q-input>

          <q-input
            v-model="password"
            label="Palavra-passe"
            outlined
            :type="showPassword ? 'text' : 'password'"
            :disable="loading"
            :rules="[(v) => !!v || 'Obrigatória']"
          >
            <template #prepend><q-icon name="lock" /></template>
            <template #append>
              <q-icon
                :name="showPassword ? 'visibility_off' : 'visibility'"
                class="cursor-pointer"
                @click="showPassword = !showPassword"
              />
            </template>
          </q-input>

          <q-banner v-if="errorMsg" dense rounded class="bg-red-1 text-red-9">
            <template #avatar><q-icon name="error" /></template>
            {{ errorMsg }}
          </q-banner>

          <q-btn
            type="submit"
            color="primary"
            label="Entrar"
            class="full-width"
            size="lg"
            :loading="loading"
          />
        </q-form>

        <q-separator class="q-my-md" />

        <q-btn
          outline
          color="teal"
          icon="explore"
          label="Explorar Demo"
          class="full-width"
          :loading="demoLoading"
          @click="handleDemo"
        />
        <div class="text-caption text-center text-grey q-mt-xs">
          Explore sem criar conta — dados de demonstração
        </div>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'

const router = useRouter()
const auth = useAuthStore()
const $q = useQuasar()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const demoLoading = ref(false)
const errorMsg = ref('')

// Restore dark mode preference
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
.login-bg {
  background: linear-gradient(135deg, #1a237e 0%, #1565c0 60%, #0277bd 100%);
}
.body--dark .login-bg {
  background: linear-gradient(135deg, #0d0d1a 0%, #0a1929 60%, #0d2137 100%);
}
</style>
