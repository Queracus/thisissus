// Thin fetch wrapper: cookies included, JSON in/out, errors carry the backend's `code`.
export async function api(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(body.code || res.statusText), { code: body.code, status: res.status })
  return body
}
