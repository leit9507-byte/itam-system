import request from '../utils/request'

export function login(payload) {
  return request.post('/auth/login', payload)
}

export function startSso(providerType) {
  return request.get(`/auth/sso/${providerType}/start`)
}

export function getUsers() {
  return request.get('/users/list')
}

export function syncUsers(payload = {}) {
  return request.post('/users/sync', payload)
}

export function getIdentityProviders() {
  return request.get('/identity/providers')
}

export function createIdentityProvider(payload) {
  return request.post('/identity/providers', payload)
}

export function updateIdentityProvider(id, payload) {
  return request.put(`/identity/providers/${id}`, payload)
}

export function testIdentityProvider(id) {
  return request.post(`/identity/providers/${id}/test`)
}
