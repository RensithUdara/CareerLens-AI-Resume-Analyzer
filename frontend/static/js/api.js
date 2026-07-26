/* Small fetch wrapper shared by every page. Cookies are sent automatically. */
async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  let data = null;
  try { data = await response.json(); } catch (_) { /* no JSON body */ }

  if (!response.ok) {
    const message = (data && data.detail) ? data.detail : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}
