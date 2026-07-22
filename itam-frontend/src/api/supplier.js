import request from '../utils/request'
import { cachedRequest, clearCache } from './cache'

const SUPPLIER_LOOKUP_LIMIT = 500

export async function getSuppliers(filters = {}) {
  const cacheKey = `supplier:lookup:${filters.keyword || ''}`
  const result = await cachedRequest(cacheKey, () => getSuppliersPaged({ ...filters, page: 1, page_size: SUPPLIER_LOOKUP_LIMIT }))
  return result.list
}

export async function getSuppliersPaged(filters = {}) {
  const result = await request.get('/supplier/list', {
    params: {
      keyword: filters.keyword || '',
      page: filters.page || undefined,
      page_size: filters.page_size ?? filters.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  return { list: rows.map(mapSupplier), total }
}

export async function getSupplierPurchaseDevices(supplierName, filters = {}) {
  const result = await request.get(`/supplier/${encodeURIComponent(supplierName)}/devices`, {
    params: {
      page: filters.page || undefined,
      page_size: filters.page_size ?? filters.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  return {
    list: rows.map(item => ({
      supplier_name: item.supplier_name,
      purchase_no: item.purchase_no,
      status: item.status,
      product_name: item.product_name,
      category: item.category,
      brand: item.brand || '',
      model: item.model || '',
      quantity: Number(item.quantity || 0),
      unit_price: Number(item.unit_price || 0),
      total_amount: Number(item.total_amount || 0),
      warehouse: item.warehouse || '',
      dept: item.dept || ''
    })),
    total
  }
}

export async function getSupplierRecycledAssets(supplierName, filters = {}) {
  const result = await request.get(`/supplier/${encodeURIComponent(supplierName)}/recycled-assets`, {
    params: {
      page: filters.page || undefined,
      page_size: filters.page_size ?? filters.pageSize ?? undefined
    }
  })
  const { rows, total } = normalizePagedResult(result)
  return {
    list: rows.map(item => ({
      request_no: item.request_no || '',
      asset_id: item.asset_id || '',
      asset_no: item.asset_no || '',
      asset_name: item.asset_name || '',
      category: item.category || '',
      brand: item.brand || '',
      model: item.model || '',
      sn: item.sn || '',
      purchase_price: Number(item.purchase_price || 0),
      estimated_residual_value: Number(item.estimated_residual_value || 0),
      final_residual_value: Number(item.final_residual_value || 0),
      retirement_date: formatDate(item.retirement_date),
      retirement_approval_no: item.retirement_approval_no || '',
      disposed_at: formatDate(item.disposed_at),
      disposal_remark: item.disposal_remark || '',
      status: item.status || ''
    })),
    total
  }
}

export async function saveSupplier(payload) {
  clearCache('supplier:')
  const body = {
    name: payload.name,
    contact: payload.contact || '',
    phone: payload.phone || '',
    level: payload.level || '普通',
    status: payload.status || '启用'
  }
  const row = payload.id ? await request.put(`/supplier/${payload.id}`, body) : await request.post('/supplier/save', body)
  return mapSupplier(row)
}

function mapSupplier(row) {
  return {
    id: row.id,
    supplier_no: row.supplier_no,
    name: row.name,
    contact: row.contact || '',
    phone: row.phone || '',
    level: row.level || '普通',
    status: row.status || '启用',
    purchase_count: Number(row.purchase_count || 0),
    device_count: Number(row.device_count || 0),
    total_amount: Number(row.total_amount || 0),
    recycle_count: Number(row.recycle_count || 0),
    recycle_amount: Number(row.recycle_amount || 0),
    last_purchase_no: row.last_purchase_no || ''
  }
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value).slice(0, 10) : date.toISOString().slice(0, 10)
}

function normalizePagedResult(result) {
  if (Array.isArray(result)) return { rows: result, total: result.length }
  const rows = result?.list || result?.items || []
  return { rows, total: Number(result?.total ?? rows.length) }
}
