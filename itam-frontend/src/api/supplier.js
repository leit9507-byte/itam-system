import { getPurchases } from './purchase'

const supplierProfiles = [
  { id: 'SUP-001', name: '联想官方渠道', contact: '渠道经理', phone: '', level: '核心', status: '启用' },
  { id: 'SUP-002', name: 'Apple 企业经销商', contact: '客户经理', phone: '', level: '核心', status: '启用' },
  { id: 'SUP-003', name: 'Dell 授权代理', contact: '销售经理', phone: '', level: '普通', status: '启用' }
]

export async function getSuppliers(filters = {}) {
  const purchases = await getPurchases()
  const map = new Map()

  supplierProfiles.forEach(profile => {
    map.set(profile.name, {
      ...profile,
      purchase_count: 0,
      device_count: 0,
      total_amount: 0,
      last_purchase_no: ''
    })
  })

  purchases.forEach(purchase => {
    const name = purchase.supplier_name || '未指定供应商'
    if (!map.has(name)) {
      map.set(name, {
        id: `SUP-${String(map.size + 1).padStart(3, '0')}`,
        name,
        contact: '',
        phone: '',
        level: '普通',
        status: '启用',
        purchase_count: 0,
        device_count: 0,
        total_amount: 0,
        last_purchase_no: ''
      })
    }
    const supplier = map.get(name)
    supplier.purchase_count += 1
    supplier.device_count += purchase.quantity
    supplier.total_amount += purchase.total_amount
    supplier.last_purchase_no = purchase.purchase_no
  })

  const keyword = (filters.keyword || '').toLowerCase()
  return Array.from(map.values()).filter(item => {
    return !keyword || [item.id, item.name, item.contact, item.level].join(' ').toLowerCase().includes(keyword)
  })
}

export async function getSupplierPurchaseDevices(supplierName) {
  const purchases = await getPurchases()
  return purchases
    .filter(purchase => (purchase.supplier_name || '未指定供应商') === supplierName)
    .flatMap(purchase => purchase.items.map(item => ({
      supplier_name: supplierName,
      purchase_no: purchase.purchase_no,
      status: purchase.status_label,
      product_name: item.product_name,
      category: item.category,
      brand: item.brand,
      model: item.model,
      quantity: item.quantity,
      unit_price: item.unit_price,
      total_amount: item.total_amount,
      warehouse: item.warehouse,
      dept: item.dept
    })))
}

export async function saveSupplier(payload) {
  const existed = supplierProfiles.find(item => item.id === payload.id)
  if (existed) Object.assign(existed, payload)
  else supplierProfiles.unshift({ ...payload, id: `SUP-${String(supplierProfiles.length + 1).padStart(3, '0')}`, status: payload.status || '启用' })
  return payload
}
