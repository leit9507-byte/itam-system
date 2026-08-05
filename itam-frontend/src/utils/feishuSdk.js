import request from './request'

const DEFAULT_SDK_URLS = [
  import.meta.env.VITE_FEISHU_SDK_URL,
  'https://lf-scm-cn.feishucdn.com/lark/op/h5-js-sdk-1.5.44.js',
  'https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.44.js'
].filter(Boolean)

let sdkLoading = null
let jsapiConfigLoading = null
let configuredUrl = ''
let lastScanError = ''

export function isFeishuClient() {
  const ua = navigator.userAgent || ''
  return /Lark|Feishu|LarkLocale/i.test(ua)
}

export function feishuRuntimeStatus() {
  return {
    isFeishu: isFeishuClient(),
    hasH5Sdk: Boolean(window.h5sdk),
    hasTt: Boolean(window.tt),
    hasLark: Boolean(window.lark),
    hasScanCode: Boolean(window.tt?.scanCode || window.lark?.scanCode),
    jsapiConfigured: Boolean(configuredUrl),
    lastError: lastScanError,
    userAgent: navigator.userAgent || ''
  }
}

export async function scanByFeishuSdk() {
  lastScanError = ''
  const bridge = await getFeishuBridge()
  if (!bridge?.scanCode) return ''
  await waitForReady(bridge)
  return callScanCode(bridge)
}

export async function prepareFeishuScanSdk() {
  if (!isFeishuClient() && import.meta.env.VITE_FEISHU_SDK_AUTO_LOAD !== 'true') return false
  try {
    const bridge = await getFeishuBridge()
    if (!bridge?.scanCode) {
      lastScanError = '飞书客户端未提供 scanCode 能力，请确认应用已发布并配置 JSAPI 权限'
      return false
    }
    await waitForReady(bridge)
    lastScanError = ''
    return true
  } catch (error) {
    lastScanError = describeError(error) || '飞书扫码能力初始化失败'
    return false
  }
}

export function getLastFeishuScanError() {
  return lastScanError
}

async function getFeishuBridge() {
  if (window.tt?.scanCode) return window.tt
  if (window.lark?.scanCode) return window.lark
  if (!isFeishuClient() && import.meta.env.VITE_FEISHU_SDK_AUTO_LOAD !== 'true') return null
  await loadFeishuSdk()
  await configureJsapi()
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

async function waitForReady(bridge) {
  await configureJsapi()
  if (!bridge?.ready) return
  return new Promise(resolve => {
    const timer = window.setTimeout(resolve, 2000)
    bridge.ready(() => {
      window.clearTimeout(timer)
      resolve()
    })
  })
}

function waitForH5SdkReady() {
  if (!window.h5sdk?.ready) return Promise.resolve()
  return new Promise(resolve => {
    const timer = window.setTimeout(resolve, 3000)
    window.h5sdk.ready(() => {
      window.clearTimeout(timer)
      resolve()
    })
  })
}

async function configureJsapi() {
  if (!window.h5sdk?.config || !isFeishuClient()) return
  const url = window.location.href.split('#')[0]
  if (configuredUrl === url) return
  if (jsapiConfigLoading) return jsapiConfigLoading
  jsapiConfigLoading = doConfigureJsapi(url)
    .finally(() => {
      jsapiConfigLoading = null
    })
  return jsapiConfigLoading
}

async function doConfigureJsapi(url) {
  let config
  try {
    config = await request.get('/scan-bindings/feishu-jsapi-signature', {
      params: { url },
      silentError: true
    })
  } catch (error) {
    const message = describeSignatureRequestError(error)
    lastScanError = message
    throw new Error(message)
  }
  await new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error('Feishu JSAPI config timeout')), 8000)
    const fail = error => {
      window.clearTimeout(timer)
      const message = describeError(error) || 'Feishu JSAPI config failed'
      lastScanError = message
      reject(new Error(message))
    }
    const success = () => {
      window.clearTimeout(timer)
      resolve()
    }
    window.h5sdk.ready?.(success)
    window.h5sdk.error?.(fail)
    window.h5sdk.config({
      appId: config.appId,
      timestamp: Number(config.timestamp),
      nonceStr: config.nonceStr,
      signature: config.signature,
      jsApiList: config.jsApiList || ['scanCode'],
      onSuccess: success,
      onFail: fail,
      success,
      fail
    })
  })
  configuredUrl = url
}

function callScanCode(bridge) {
  return new Promise(resolve => {
    let settled = false
    const timer = window.setTimeout(() => {
      finish('', new Error('飞书扫码调用超时，请关闭当前页面后从飞书工作台重新进入'))
    }, 15000)
    const finish = (value, error) => {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      const text = extractScanText(value)
      if (text) lastScanError = ''
      else if (error) lastScanError = describeError(error)
      else lastScanError = ''
      resolve(text)
    }
    const options = {
      scanType: ['qrCode', 'barCode'],
      success: finish,
      fail: error => finish('', error),
      cancel: error => finish('', error || 'cancel'),
      complete: result => {
        if (!settled && extractScanText(result)) finish(result)
      }
    }
    try {
      const result = bridge.scanCode(options)
      if (result?.then) result.then(finish).catch(error => finish('', error))
    } catch (error) {
      finish('', error)
    }
  })
}

function extractScanText(result) {
  if (!result) return ''
  if (typeof result === 'string') return result
  return result.result || result.text || result.rawValue || result.code || result.resultStr || result.data?.result || result.data?.text || ''
}

function describeError(error) {
  if (!error) return ''
  if (typeof error === 'string') return error
  if (error.userMessage) return error.userMessage
  const details = [error.errMsg, error.errString, error.message]
    .filter(Boolean)
    .filter((value, index, rows) => rows.indexOf(value) === index)
  const codes = [error.errno, error.errCode, error.errorCode]
    .filter(value => value !== undefined && value !== null && value !== '')
  if (details.length || codes.length) {
    return [details.join('；'), codes.length ? `错误码：${codes.join('/')}` : ''].filter(Boolean).join('；')
  }
  try {
    return JSON.stringify(error)
  } catch {
    return String(error)
  }
}

function describeSignatureRequestError(error) {
  if (error?.response?.status === 404) {
    return 'JSAPI 签名接口返回 404，请检查网关是否将 /backend 转发到 ITAM 后端'
  }
  return describeError(error) || '无法获取飞书 JSAPI 签名参数'
}
