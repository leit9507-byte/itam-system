const cache = new Map()
const DEFAULT_TTL = 60 * 1000

export function cachedRequest(key, loader, ttl = DEFAULT_TTL) {
  const now = Date.now()
  const hit = cache.get(key)
  if (hit && hit.expiresAt > now) {
    return hit.promise
  }
  const promise = Promise.resolve()
    .then(loader)
    .catch(error => {
      cache.delete(key)
      throw error
    })
  cache.set(key, { promise, expiresAt: now + ttl })
  return promise
}

export function clearCache(prefix = '') {
  for (const key of cache.keys()) {
    if (!prefix || key.startsWith(prefix)) {
      cache.delete(key)
    }
  }
}
