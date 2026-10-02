import { startAuthentication, startRegistration } from '@simplewebauthn/browser'
import { useQuery } from '@tanstack/react-query'
import { api } from './api.js'
import { disablePush } from './push.js'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body ?? {}) })

// Current user, or null when logged out.
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    retry: false,
    queryFn: () => api('/auth/me').catch((e) => (e.status === 401 ? null : Promise.reject(e))),
  })
}

export async function registerPasskey(token) {
  const optionsJSON = await post('/auth/passkey/register/options', { token })
  const credential = await startRegistration({ optionsJSON })
  return post('/auth/passkey/register/verify', { token, credential })
}

export async function loginWithPasskey() {
  const optionsJSON = await post('/auth/passkey/login/options')
  const credential = await startAuthentication({ optionsJSON })
  return post('/auth/passkey/login/verify', { credential })
}

export const loginWithPin = (username, pin) => post('/auth/pin/login', { username, pin })

export const setPin = (username, pin) => api('/me/pin', { method: 'PUT', body: JSON.stringify({ username, pin }) })

export async function logout() {
  await disablePush().catch(() => {})
  return post('/auth/logout')
}
