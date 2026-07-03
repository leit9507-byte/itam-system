import request from '../utils/request'

export function getNotificationSetting() {
  return request.get('/notification/settings')
}

export function saveNotificationSetting(payload) {
  return request.post('/notification/settings', payload)
}

export function getNotificationPreviews() {
  return request.get('/notification/previews')
}

export function testNotification(message) {
  return request.post('/notification/test', { message })
}
