import request from '../utils/request'

export function login(payload) {
  return request.post('/auth/login', payload)
}

export function getCurrentPermissions() {
  return request.get('/auth/me/permissions', { silentError: true })
}

export function startSso(providerType) {
  return request.get(`/auth/sso/${providerType}/start`)
}

export function startSsoWithState(providerType, state, redirectUri) {
  return request.get(`/auth/sso/${providerType}/start`, { params: { state, redirect_uri: redirectUri } })
}

export function completeSso(providerType, params) {
  return request.get(`/auth/callback/${providerType}`, { params })
}

export function getFeishuLoginFreeConfig() {
  return request.get('/auth/feishu/login-free/config', { silentError: true })
}

export function feishuLoginFree(payload) {
  return request.post('/auth/feishu/login-free', payload)
}

export function getUsers() {
  return request.get('/users/list')
}

export function saveUser(payload) {
  return request.post('/users/save', payload)
}

export function deleteUser(userId) {
  return request.delete(`/users/${encodeURIComponent(userId)}`)
}

export function updateUserPermissions(userId, payload) {
  return request.put(`/users/${encodeURIComponent(userId)}/permissions`, payload)
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

export function deleteIdentityProvider(id) {
  return request.delete(`/identity/providers/${id}`)
}

export function testIdentityProvider(id) {
  return request.post(`/identity/providers/${id}/test`)
}

export function getRolePermissions() {
  return request.get('/rbac/permissions')
}

export function saveRolePermissions(payload) {
  return request.post('/rbac/permissions', payload)
}
