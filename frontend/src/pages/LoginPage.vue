<template>
  <q-page class="flex flex-center bg-grey-2">
    <q-card style="min-width: 360px; max-width: 400px; width: 100%">
      <q-card-section class="bg-primary text-white text-center q-pb-lg">
        <q-icon name="schedule" size="48px" />
        <div class="text-h6 q-mt-sm">Gerador de Horários</div>
        <div class="text-caption">Acesso ao sistema</div>
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
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const errorMsg = ref('')

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
</script>
