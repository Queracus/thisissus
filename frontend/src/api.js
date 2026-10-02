// Thin fetch wrapper: cookies included, JSON in/out, errors carry the backend's `code`.
// The active space travels as X-Space-Id on every request (set by SpaceProvider).
let spaceId = null
export const setSpaceId = (id) => { spaceId = id }

export async function api(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(spaceId && { 'X-Space-Id': String(spaceId) }), ...options.headers },
    ...options,
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(body.code || res.statusText), { code: body.code, status: res.status, body })
  return body
}
