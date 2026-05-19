<template>
  <q-page padding>
    <div class="row items-center q-mb-lg">
      <q-icon name="settings" size="28px" color="primary" class="q-mr-sm" />
      <div class="text-h5">Configurações</div>
    </div>

    <div class="row justify-center">
      <div style="max-width: 640px; width: 100%">

        <!-- Pushbullet notifications -->
        <q-card flat bordered class="q-mb-md">
          <q-card-section>
            <div class="row items-center q-mb-md">
              <q-icon name="notifications" color="teal-7" size="24px" class="q-mr-sm" />
              <div class="text-subtitle1 text-weight-bold">Notificações Pushbullet</div>
            </div>
            <div class="text-body2 text-grey-7 q-mb-md">
              Receba uma notificação no telemóvel ou PC quando a geração de horários terminar.
              Para obter o token, aceda a
              <a href="https://www.pushbullet.com/#settings/account" target="_blank" class="text-primary">pushbullet.com → Account → Access Tokens</a>.
            </div>

            <q-input
              v-model="pushbulletToken"
              label="Access Token do Pushbullet"
              outlined
              dense
              :type="showToken ? 'text' : 'password'"
              placeholder="o.XXXXXXXXXXXXXXXXXXXXXXXX"
              class="q-mb-sm"
            >
              <template #append>
                <q-btn flat round dense :icon="showToken ? 'visibility_off' : 'visibility'" @click="showToken = !showToken" />
              </template>
            </q-input>

            <div class="row q-gutter-sm q-mt-sm">
              <q-btn color="primary" icon="save" label="Guardar" :loading="saving" @click="saveToken" :disable="!pushbulletToken && !originalToken" />
              <q-btn color="teal-7" icon="send" label="Testar" :loading="testing" @click="testNotification" :disable="!pushbulletToken" />
              <q-btn v-if="originalToken" flat color="negative" icon="delete" label="Remover" @click="removeToken" />
            </div>

            <q-banner v-if="testResult" rounded class="q-mt-md" :class="testResult === 'ok' ? 'bg-positive text-white' : 'bg-negative text-white'">
              <template #avatar>
                <q-icon :name="testResult === 'ok' ? 'check_circle' : 'error'" />
              </template>
              {{ testResult === 'ok' ? 'Notificação enviada com sucesso! Verifique o seu dispositivo.' : testError }}
            </q-banner>

            <q-banner v-if="originalToken" rounded class="bg-teal-1 text-teal-9 q-mt-md">
              <template #avatar><q-icon name="check_circle" color="teal-7" /></template>
              Pushbullet configurado — receberá notificações quando os horários terminarem de gerar.
            </q-banner>
          </q-card-section>
        </q-card>

      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

const $q = useQuasar()

const pushbulletToken = ref('')
const originalToken = ref('')
const showToken = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<'ok' | 'error' | null>(null)
const testError = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get('/settings')
    if (data.pushbullet_token) {
      originalToken.value = data.pushbullet_token
      pushbulletToken.value = data.pushbullet_token
    }
  } catch { /* ignore */ }
})

async function saveToken() {
  saving.value = true
  try {
    await api.put('/settings/pushbullet_token', { value: pushbulletToken.value || null })
    originalToken.value = pushbulletToken.value
    $q.notify({ type: 'positive', message: 'Token guardado' })
    testResult.value = null
  } catch {
    $q.notify({ type: 'negative', message: 'Erro ao guardar' })
  } finally {
    saving.value = false
  }
}

async function removeToken() {
  await api.put('/settings/pushbullet_token', { value: null })
  pushbulletToken.value = ''
  originalToken.value = ''
  testResult.value = null
  $q.notify({ type: 'positive', message: 'Token removido' })
}

async function testNotification() {
  testing.value = true
  testResult.value = null
  try {
    await api.post('/settings/test-pushbullet', { token: pushbulletToken.value })
    testResult.value = 'ok'
  } catch (err: unknown) {
    testResult.value = 'error'
    testError.value = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erro desconhecido'
  } finally {
    testing.value = false
  }
}
</script>
