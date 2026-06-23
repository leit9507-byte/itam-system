import request from '../utils/request'

export function getDeviceTypes() {
  return request.get('/catalog/device-types')
}

export function createDeviceType(payload) {
  return request.post('/catalog/device-types', payload)
}

export function updateDeviceType(id, payload) {
  return request.put(`/catalog/device-types/${id}`, payload)
}

export function getProducts() {
  return request.get('/catalog/products')
}

export function createProduct(payload) {
  return request.post('/catalog/products', payload)
}

export function updateProduct(id, payload) {
  return request.put(`/catalog/products/${id}`, payload)
}
