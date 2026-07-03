export function parseAssetCode(value) {
  const text = String(value || '').trim()
  if (!text) return ''

  const tagged = text.match(/ITAM-ASSET:([^|]+)/i)
  if (tagged?.[1]) return tagged[1].trim()

  try {
    const url = new URL(text)
    const queryCode = ['asset_id', 'assetId', 'code', 'sn', 'id'].map(key => url.searchParams.get(key)).find(Boolean)
    if (queryCode) return queryCode.trim()

    const segments = url.pathname.split('/').filter(Boolean)
    const assetSegmentIndex = segments.findIndex(item => ['hardware', 'asset', 'assets'].includes(item.toLowerCase()))
    return (assetSegmentIndex >= 0 ? segments[assetSegmentIndex + 1] : segments.at(-1))?.trim() || text
  } catch {
    return text
  }
}

export function assetCodeCandidates(value) {
  const code = parseAssetCode(value)
  if (!code) return []

  const candidates = new Set([code])
  if (/^\d+$/.test(code)) {
    candidates.add(`ITAM-${code.padStart(6, '0')}`)
    candidates.add(`ITAM-${code.padStart(4, '0')}`)
    candidates.add(`HW-${code}`)
    candidates.add(`HARDWARE-${code}`)
  }
  return [...candidates].filter(Boolean)
}

export function assetCodeMatches(asset, value) {
  const candidates = assetCodeCandidates(value).map(item => String(item).trim().toLowerCase())
  const fields = [asset?.asset_id, asset?.sn, asset?.id, asset?.hardware_id, asset?.legacy_id]
    .filter(Boolean)
    .map(item => String(item).trim().toLowerCase())

  return fields.some(field => candidates.some(candidate => field === candidate || field.endsWith(`-${candidate}`)))
}
