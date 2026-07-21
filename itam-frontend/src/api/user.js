import request from '../utils/request'
import { cachedRequest, clearCache } from './cache'

export function login(payload) {
  return request.post('/auth/login', payload)
}

export function getCurrentPermissions() {
  return request.get('/auth/me/permissions', { silentError: true })
}

export function getUsers() {
  return cachedRequest('identity:users', () => request.get('/users/list'))
}

export function saveUser(payload) {
  clearCache('identity:')
  return request.post('/users/save', payload)
}

export function deleteUser(userId) {
  clearCache('identity:')
  return request.delete(`/users/${encodeURIComponent(userId)}`)
}

export function updateUserPermissions(userId, payload) {
  clearCache('identity:')
  return request.put(`/users/${encodeURIComponent(userId)}/permissions`, payload)
}

export function updateUserAssetAssignment(userId, payload) {
  clearCache('identity:')
  return request.put(`/users/${encodeURIComponent(userId)}/asset-assignment`, payload)
}

export function syncUsers(payload = {}) {
  clearCache('identity:')
  return request.post('/users/sync', payload)
}

export function getIdentityProviders() {
  return cachedRequest('identity:providers', () => request.get('/identity/providers'))
}

export function createIdentityProvider(payload) {
  clearCache('identity:')
  return request.post('/identity/providers', payload)
}

export function updateIdentityProvider(id, payload) {
  clearCache('identity:')
  return request.put(`/identity/providers/${id}`, payload)
}

export function deleteIdentityProvider(id) {
  clearCache('identity:')
  return request.delete(`/identity/providers/${id}`)
}

export function testIdentityProvider(id) {
  return request.post(`/identity/providers/${id}/test`)
}

export function getRolePermissions() {
  return cachedRequest('identity:role-permissions', () => request.get('/rbac/permissions'))
}

export function saveRolePermissions(payload) {
  clearCache('identity:')
  return request.post('/rbac/permissions', payload)
}
