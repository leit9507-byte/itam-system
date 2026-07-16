import request from '../utils/request'
import { cachedRequest, clearCache } from './cache'

export function getLocations(keyword = '') {
  const cleanKeyword = keyword || ''
  return cachedRequest(`location:list:${cleanKeyword}`, () => request.get('/location/list', { params: { keyword: cleanKeyword || undefined } }))
}

export function createLocation(payload) {
  clearCache('location:')
  return request.post('/location/save', normalizeLocation(payload))
}

export function updateLocation(id, payload) {
  clearCache('location:')
  return request.put(`/location/${id}`, normalizeLocation(payload))
}

export function deleteLocation(id) {
  clearCache('location:')
  return request.delete(`/location/${id}`)
}

function normalizeLocation(payload) {
  return {
    name: payload.name || '',
    code: payload.code || '',
    type: payload.type || '办公位置',
    owner_dept: payload.owner_dept || '',
    description: payload.description || '',
    status: payload.status || '启用'
  }
}
