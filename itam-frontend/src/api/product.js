import request from '../utils/request'
import { cachedRequest, clearCache } from './cache'

export function getDeviceTypes() {
  return cachedRequest('catalog:device-types', () => request.get('/catalog/device-types'))
}

export function createDeviceType(payload) {
  clearCache('catalog:')
  return request.post('/catalog/device-types', payload)
}

export function updateDeviceType(id, payload) {
  clearCache('catalog:')
  return request.put(`/catalog/device-types/${id}`, payload)
}

export function deleteDeviceType(id) {
  clearCache('catalog:')
  return request.delete(`/catalog/device-types/${id}`)
}

export function getProducts() {
  return cachedRequest('catalog:products', () => request.get('/catalog/products'))
}

export function createProduct(payload) {
  clearCache('catalog:')
  return request.post('/catalog/products', payload)
}

export function updateProduct(id, payload) {
  clearCache('catalog:')
  return request.put(`/catalog/products/${id}`, payload)
}

export function deleteProduct(id) {
  clearCache('catalog:')
  return request.delete(`/catalog/products/${id}`)
}
