const memoryStorage = new Map()

export function getStorageItem(key) {
  try {
    const value = window.localStorage.getItem(key)
    return value === null ? memoryStorage.get(key) ?? null : value
  } catch {
    return memoryStorage.get(key) ?? null
  }
}

export function setStorageItem(key, value) {
  const normalized = String(value)
  memoryStorage.set(key, normalized)
  try {
    window.localStorage.setItem(key, normalized)
  } catch {
    // Some embedded WebViews disable persistent storage. Memory fallback keeps the current session usable.
  }
}

export function removeStorageItem(key) {
  memoryStorage.delete(key)
  try {
    window.localStorage.removeItem(key)
  } catch {
    // The key is already absent from the in-memory fallback.
  }
}

export function getStorageJson(key, fallback) {
  const raw = getStorageItem(key)
  if (!raw) return fallback
  try {
    return JSON.parse(raw)
  } catch {
    removeStorageItem(key)
    return fallback
  }
}
