import request from '../utils/request'

export function getLocations(keyword = '') {
  return request.get('/location/list', { params: { keyword: keyword || undefined } })
}

export function createLocation(payload) {
  return request.post('/location/save', normalizeLocation(payload))
}

export function updateLocation(id, payload) {
  return request.put(`/location/${id}`, normalizeLocation(payload))
}

export function deleteLocation(id) {
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
