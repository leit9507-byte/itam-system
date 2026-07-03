const DEFAULT_SDK_URLS = [
  import.meta.env.VITE_FEISHU_SDK_URL,
  'https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.30.js',
  'https://lf3-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.30.js'
].filter(Boolean)

let sdkLoading = null

export function isFeishuClient() {
  const ua = navigator.userAgent || ''
  return /Lark|Feishu|LarkLocale/i.test(ua)
}

export async function scanByFeishuSdk() {
  const bridge = await getFeishuBridge()
  if (!bridge?.scanCode) return ''
  await waitForReady(bridge)
  return callScanCode(bridge)
}

async function getFeishuBridge() {
  if (window.tt?.scanCode) return window.tt
  if (window.lark?.scanCode) return window.lark
  if (!isFeishuClient() && import.meta.env.VITE_FEISHU_SDK_AUTO_LOAD !== 'true') return null
  await loadFeishuSdk()
  return window.tt?.scanCode ? window.tt : window.lark?.scanCode ? window.lark : null
}

function loadFeishuSdk() {
  if (window.tt?.scanCode || window.lark?.scanCode) return Promise.resolve()
  if (sdkLoading) return sdkLoading
  sdkLoading = loadFirstAvailable(DEFAULT_SDK_URLS)
  return sdkLoading
}

async function loadFirstAvailable(urls) {
  let lastError = null
  for (const url of urls) {
    try {
      await loadScript(url)
      if (window.tt || window.lark) return
    } catch (error) {
      lastError = error
    }
  }
  throw lastError || new Error('Feishu JS SDK load failed')
}

function loadScript(src) {
  const existed = document.querySelector(`script[data-feishu-sdk="${src}"]`)
  if (existed) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.defer = true
    script.dataset.feishuSdk = src
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Feishu JS SDK load failed: ${src}`))
    document.head.appendChild(script)
  })
}

function waitForReady(bridge) {
  if (!bridge?.ready) return Promise.resolve()
  return new Promise(resolve => {
    const timer = window.setTimeout(resolve, 2000)
    bridge.ready(() => {
      window.clearTimeout(timer)
      resolve()
    })
  })
}

function callScanCode(bridge) {
  return new Promise(resolve => {
    let settled = false
    const finish = value => {
      if (settled) return
      settled = true
      resolve(extractScanText(value))
    }
    const options = {
      scanType: ['qrCode', 'barCode'],
      success: finish,
      fail: () => finish(''),
      cancel: () => finish(''),
      complete: result => {
        if (!settled && extractScanText(result)) finish(result)
      }
    }
    try {
      const result = bridge.scanCode(options)
      if (result?.then) result.then(finish).catch(() => finish(''))
    } catch {
      finish('')
    }
  })
}

function extractScanText(result) {
  if (!result) return ''
  if (typeof result === 'string') return result
  return result.result || result.text || result.rawValue || result.code || result.resultStr || result.data?.result || result.data?.text || ''
}
