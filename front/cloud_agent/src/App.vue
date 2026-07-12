<template>
  <div v-if="!currentUser" class="login-page">
    <section class="login-shell">
      <div class="login-hero">
        <div class="brand-row">
          <div class="brand-logo">CA</div>
          <div>
            <h1>Cloud Agent</h1>
            <p>企业云智能客服工作台</p>
          </div>
        </div>
        <div class="hero-copy">
          <h2>统一管理云产品咨询、账单查询和智能推荐</h2>
          <p>登录后可查看历史会话，跨设备继续之前的问题，并按用户隔离所有聊天记录。</p>
        </div>
      </div>

      <div class="login-panel">
        <div class="login-title">
          <h2>账号登录</h2>
          <p>使用预置账号进入客服工作台</p>
        </div>
        <el-form class="login-form" @submit.prevent="login">
          <el-form-item>
            <el-input v-model="loginForm.username" size="large" placeholder="用户名">
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-input v-model="loginForm.password" size="large" type="password" show-password placeholder="密码">
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-button class="login-button" type="primary" size="large" :loading="isAuthLoading" @click="login">
            登录
          </el-button>
        </el-form>
        <p class="login-hint">默认账号：user_1001 / user_1002，密码：Cloud@123456</p>
      </div>
    </section>
  </div>

  <div v-else class="chat-container">
    <el-container class="app-shell">
      <el-aside class="sidebar desktop-sidebar" width="300px">
        <div class="sidebar-content">
          <div class="sidebar-header">
            <div class="brand">
              <div class="brand-logo">CA</div>
              <h2>Cloud Agent</h2>
            </div>
            <el-button :icon="Plus" circle type="primary" title="新建对话" @click="createNewSession" />
          </div>

          <div class="session-list">
            <div
              v-for="session in sessions"
              :key="session.session_id"
              :class="['session-item', { active: currentSessionId === session.session_id }]"
              @click="switchSession(session.session_id)"
            >
              <el-icon class="session-icon"><ChatDotRound /></el-icon>
              <div class="session-copy">
                <span class="session-name">{{ displaySessionTitle(session) }}</span>
                <span class="session-preview">{{ session.last_message || '暂无消息' }}</span>
              </div>
              <el-button class="delete-session" :icon="Delete" text circle title="删除对话" @click.stop="deleteSession(session.session_id)" />
            </div>
          </div>

          <div class="user-info">
            <div class="mini-avatar user-avatar">{{ userInitial }}</div>
            <div class="user-copy">
              <strong>{{ currentUser.display_name }}</strong>
              <span>{{ currentUser.username }}</span>
            </div>
          </div>
        </div>
      </el-aside>

      <el-drawer v-model="isSessionDrawerOpen" direction="ltr" size="82%" :with-header="false" class="mobile-drawer">
        <div class="sidebar-content drawer-sidebar">
          <div class="sidebar-header">
            <div class="brand">
              <div class="brand-logo">CA</div>
              <h2>Cloud Agent</h2>
            </div>
            <el-button :icon="Plus" circle type="primary" title="新建对话" @click="createNewSession(); isSessionDrawerOpen = false" />
          </div>

          <div class="session-list">
            <div
              v-for="session in sessions"
              :key="session.session_id"
              :class="['session-item', { active: currentSessionId === session.session_id }]"
              @click="switchSession(session.session_id); isSessionDrawerOpen = false"
            >
              <el-icon class="session-icon"><ChatDotRound /></el-icon>
              <div class="session-copy">
                <span class="session-name">{{ displaySessionTitle(session) }}</span>
                <span class="session-preview">{{ session.last_message || '暂无消息' }}</span>
              </div>
              <el-button class="delete-session" :icon="Delete" text circle title="删除对话" @click.stop="deleteSession(session.session_id)" />
            </div>
          </div>

          <div class="user-info">
            <div class="mini-avatar user-avatar">{{ userInitial }}</div>
            <div class="user-copy">
              <strong>{{ currentUser.display_name }}</strong>
              <span>{{ currentUser.username }}</span>
            </div>
          </div>
        </div>
      </el-drawer>

      <el-main class="chat-main">
        <header class="chat-header">
          <el-button class="mobile-menu" :icon="Menu" circle @click="isSessionDrawerOpen = true" />
          <div class="header-copy">
            <div class="header-title">{{ activeSessionTitle }}</div>
            <div class="header-subtitle">Multi-Agent · Billing · Promotion · FinOps</div>
          </div>
          <div class="header-user">
            <span>{{ currentUser.display_name }}</span>
            <el-button :icon="SwitchButton" circle title="退出登录" @click="logout" />
          </div>
        </header>

        <div class="message-list" ref="messageListRef">
          <div v-if="messages.length === 0" class="empty-state">
            <el-icon size="56" color="#2563eb"><Service /></el-icon>
            <h3>欢迎使用云平台智能客服</h3>
            <p>可以直接提问，也可以从典型场景开始。</p>
            <div class="scenario-grid">
              <button v-for="item in scenarios" :key="item" class="scenario-item" @click="sendQuery(item)">
                {{ item }}
              </button>
            </div>
          </div>

          <div v-for="(msg, index) in messages" :key="msg.local_id || index" :class="['message-row', msg.role]">
            <div :class="['msg-avatar', msg.role === 'user' ? 'user-avatar' : 'ai-avatar']">
              {{ msg.role === 'user' ? userInitial : 'AI' }}
            </div>
            <div class="message-bubble">
              <div v-if="msg.content" v-html="renderMarkdown(msg.content)"></div>
              <div v-else-if="msg.status" class="status-line">
                <el-icon class="is-loading"><Loading /></el-icon>
                {{ msg.status }}
              </div>
              <div v-if="msg.content && msg.status" class="status-footer">
                <el-icon class="is-loading"><Loading /></el-icon>
                {{ msg.status }}
              </div>
            </div>
          </div>
        </div>

        <footer class="input-area">
          <el-input
            v-model="inputQuery"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 5 }"
            placeholder="请输入您的问题，Shift + Enter 换行，Enter 发送"
            :disabled="isChatLoading"
            @keydown.enter.prevent="handleEnter"
          />
          <el-button
            type="primary"
            class="send-btn"
            :icon="Position"
            :loading="isChatLoading"
            :disabled="!inputQuery.trim()"
            @click="sendQuery(inputQuery)"
          >
            发送
          </el-button>
        </footer>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, Delete, Loading, Lock, Menu, Plus, Position, Service, SwitchButton, User } from '@element-plus/icons-vue'
import { marked } from 'marked'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'
const ACCESS_TOKEN_KEY = 'cloud_agent_access_token'
const REFRESH_TOKEN_KEY = 'cloud_agent_refresh_token'

interface UserInfo {
  user_id: string
  username: string
  display_name: string
}

interface ChatSession {
  session_id: string
  title: string
  created_at: string
  updated_at: string
  last_message?: string
  message_count: number
}

interface Message {
  id?: number
  local_id?: string
  role: 'user' | 'assistant'
  content: string
  status?: string
  created_at?: string
}

const loginForm = ref({ username: 'user_1001', password: 'Cloud@123456' })
const accessToken = ref(localStorage.getItem(ACCESS_TOKEN_KEY) || '')
const refreshToken = ref(localStorage.getItem(REFRESH_TOKEN_KEY) || '')
const currentUser = ref<UserInfo | null>(null)
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref('')
const messages = ref<Message[]>([])
const inputQuery = ref('')
const isAuthLoading = ref(false)
const isChatLoading = ref(false)
const isSessionDrawerOpen = ref(false)
const messageListRef = ref<HTMLElement | null>(null)
const DEFAULT_SESSION_TITLE = '\u65b0\u5bf9\u8bdd'

const scenarios = [
  '云服务器ECS有哪些基本属性？',
  '帮我查一下我最近的订单记录',
  '查询我名下的所有运行中的实例',
  '获取近7天CPU/内存/带宽数据并做降本建议',
  '我是Java接口服务+MySQL，8核16G够吗？推荐具体实例型号。',
  '我想推广云服务器ECS，有海报吗？',
]

const activeSessionTitle = computed(() => {
  return displaySessionTitle(sessions.value.find((item) => item.session_id === currentSessionId.value))
})

const userInitial = computed(() => currentUser.value?.display_name?.slice(0, 1).toUpperCase() || 'U')

function displaySessionTitle(session?: Pick<ChatSession, 'title'> | null) {
  const title = session?.title?.trim()
  if (!title || /^[?\uFF1F]+$/.test(title)) return DEFAULT_SESSION_TITLE
  return title
}

onMounted(async () => {
  if (!accessToken.value || !refreshToken.value) return
  try {
    await bootstrap()
  } catch {
    clearAuth()
  }
})

function storeTokens(payload: any) {
  accessToken.value = payload.access_token
  refreshToken.value = payload.refresh_token
  localStorage.setItem(ACCESS_TOKEN_KEY, payload.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, payload.refresh_token)
}

function clearAuth() {
  accessToken.value = ''
  refreshToken.value = ''
  currentUser.value = null
  sessions.value = []
  messages.value = []
  currentSessionId.value = ''
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

async function apiFetch(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(options.headers || {})
  if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json')
  if (accessToken.value) headers.set('Authorization', `Bearer ${accessToken.value}`)
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  if (response.status !== 401 || !retry || !refreshToken.value) return response
  const refreshed = await refreshAccessToken()
  if (!refreshed) return response
  return apiFetch(path, options, false)
}

async function refreshAccessToken() {
  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken.value }),
  })
  if (!response.ok) {
    clearAuth()
    return false
  }
  const data = await response.json()
  storeTokens(data)
  currentUser.value = data.user
  return true
}

async function login() {
  if (!loginForm.value.username.trim() || !loginForm.value.password) return
  isAuthLoading.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(loginForm.value),
    })
    if (!response.ok) throw new Error('用户名或密码错误')
    const data = await response.json()
    storeTokens(data)
    currentUser.value = data.user
    await loadSessions()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    isAuthLoading.value = false
  }
}

async function bootstrap() {
  const meResponse = await apiFetch('/api/auth/me')
  if (!meResponse.ok) throw new Error('登录已过期')
  currentUser.value = await meResponse.json()
  await loadSessions()
}

async function logout() {
  try {
    if (refreshToken.value) {
      await apiFetch('/api/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken.value }),
      }, false)
    }
  } finally {
    clearAuth()
  }
}

async function loadSessions() {
  await refreshSessions()
  const firstSession = sessions.value[0]
  if (firstSession) {
    await switchSession(firstSession.session_id)
  } else {
    messages.value = []
    currentSessionId.value = ''
  }
}

async function refreshSessions() {
  const response = await apiFetch('/api/sessions')
  if (!response.ok) throw new Error('加载会话失败')
  sessions.value = await response.json()
}

async function createNewSession() {
  const response = await apiFetch('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({ title: '新对话' }),
  })
  if (!response.ok) {
    ElMessage.error('新建会话失败')
    return
  }
  const session = await response.json()
  sessions.value.unshift({ ...session, message_count: 0, last_message: '' })
  currentSessionId.value = session.session_id
  messages.value = []
}

async function switchSession(sessionId: string) {
  currentSessionId.value = sessionId
  const response = await apiFetch(`/api/sessions/${sessionId}/messages`)
  if (!response.ok) {
    ElMessage.error('加载消息失败')
    return
  }
  messages.value = (await response.json()).map((item: any) => ({
    id: item.id,
    role: item.role,
    content: item.content,
    created_at: item.created_at,
  }))
  scrollToBottom()
}

async function deleteSession(sessionId: string) {
  try {
    await ElMessageBox.confirm('删除后该对话将不再显示，是否继续？', '删除对话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const response = await apiFetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
  if (!response.ok) {
    ElMessage.error('删除失败')
    return
  }
  sessions.value = sessions.value.filter((item) => item.session_id !== sessionId)
  if (currentSessionId.value === sessionId) {
    if (sessions.value[0]) {
      await switchSession(sessions.value[0].session_id)
    } else {
      currentSessionId.value = ''
      messages.value = []
    }
  }
}

function renderMarkdown(text: string) {
  return marked.parse(text) as string
}

async function scrollToBottom() {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

function handleEnter(e: KeyboardEvent) {
  if (e.shiftKey) return
  if (inputQuery.value.trim() && !isChatLoading.value) {
    sendQuery(inputQuery.value)
  }
}

async function ensureSession() {
  if (!currentSessionId.value) await createNewSession()
  return currentSessionId.value
}

async function sendQuery(query: string) {
  const text = query.trim()
  if (!text || isChatLoading.value) return

  const sessionId = await ensureSession()
  if (!sessionId) return

  inputQuery.value = ''
  messages.value.push({ local_id: `u_${Date.now()}`, role: 'user', content: text })
  const assistantMessage: Message = {
    local_id: `a_${Date.now()}`,
    role: 'assistant',
    content: '',
    status: '正在连接...',
  }
  messages.value.push(assistantMessage)
  const assistantIndex = messages.value.length - 1
  isChatLoading.value = true
  scrollToBottom()

  try {
    let response = await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ query: text, session_id: sessionId }),
    })
    if (response.status === 401 && await refreshAccessToken()) {
      response = await apiFetch('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ query: text, session_id: sessionId }),
      }, false)
    }
    if (!response.ok || !response.body) throw new Error(`请求失败：${response.status}`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6).trim()
        if (!raw) continue
        const data = JSON.parse(raw)
        const target = messages.value[assistantIndex]
        if (!target) continue
        if (data.type === 'status') {
          target.status = data.message
        } else if (data.type === 'content') {
          target.content += data.content || ''
        } else if (data.type === 'error') {
          target.content = data.message || '请求失败'
          target.status = ''
        } else if (data.type === 'done') {
          target.status = ''
        }
        scrollToBottom()
      }
    }
    await refreshSessions()
    currentSessionId.value = sessionId
  } catch (error) {
    const target = messages.value[assistantIndex]
    if (target) {
      target.content = error instanceof Error ? error.message : '请求失败，请稍后重试'
      target.status = ''
    }
  } finally {
    isChatLoading.value = false
    const target = messages.value[assistantIndex]
    if (target) target.status = ''
    scrollToBottom()
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #eef4fb;
  padding: 32px;
  display: grid;
  place-items: center;
}

.login-shell {
  width: min(1280px, 100%);
  min-height: 680px;
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) 460px;
  background: #fff;
  border: 1px solid #dce6f2;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.12);
}

.login-hero {
  background: #101827;
  color: #e5edf7;
  padding: 56px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.brand-row,
.brand,
.user-info,
.chat-header,
.status-line,
.status-footer {
  display: flex;
  align-items: center;
}

.brand-row {
  gap: 12px;
}

.brand-row h1,
.brand h2,
.login-title h2,
.hero-copy h2 {
  margin: 0;
}

.brand-row p,
.login-title p,
.hero-copy p {
  margin: 6px 0 0;
}

.hero-copy {
  max-width: 640px;
}

.hero-copy h2 {
  color: #fff;
  font-size: 42px;
  line-height: 1.18;
  font-weight: 700;
}

.hero-copy p {
  color: #b6c6d9;
  font-size: 17px;
  line-height: 1.8;
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  color: #fff;
  background: #2563eb;
  font-weight: 700;
  flex-shrink: 0;
}

.login-panel {
  padding: 64px 52px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-title {
  margin-bottom: 28px;
}

.login-title h2 {
  color: #0f172a;
  font-size: 28px;
  font-weight: 700;
}

.login-title p,
.login-hint {
  color: #64748b;
}

.login-button {
  width: 100%;
}

.login-hint {
  font-size: 13px;
  margin: 16px 0 0;
}

.chat-container {
  height: 100vh;
  width: 100vw;
  background: #eef4fb;
  overflow: hidden;
  padding: 14px;
  box-sizing: border-box;
}

.app-shell {
  height: 100%;
  background: #fff;
  border: 1px solid #dce6f2;
  border-radius: 8px;
  overflow: hidden;
}

.sidebar,
.sidebar-content {
  height: 100%;
  background: #101827;
  color: #e5edf7;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  height: 66px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.brand {
  gap: 10px;
}

.brand h2 {
  font-size: 16px;
  color: #f8fafc;
  font-weight: 700;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.session-item {
  display: grid;
  grid-template-columns: 22px 1fr 30px;
  gap: 8px;
  align-items: center;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  color: #cbd5e1;
}

.session-item:hover,
.session-item.active {
  background: rgba(96, 165, 250, 0.18);
  color: #fff;
}

.session-icon {
  width: 18px;
  height: 18px;
  font-size: 18px;
}

.session-copy {
  min-width: 0;
}

.session-name,
.session-preview {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-name {
  font-size: 14px;
  font-weight: 600;
}

.session-preview {
  margin-top: 4px;
  font-size: 12px;
  color: #94a3b8;
}

.delete-session {
  width: 28px;
  height: 28px;
  opacity: 0.8;
}

.user-info {
  gap: 10px;
  padding: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.mini-avatar,
.msg-avatar {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  font-weight: 700;
}

.mini-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
}

.user-copy {
  min-width: 0;
}

.user-copy strong,
.user-copy span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-copy strong {
  color: #f8fafc;
  font-weight: 700;
}

.user-copy span {
  color: #94a3b8;
  font-size: 12px;
}

.chat-main {
  display: flex;
  flex-direction: column;
  padding: 0;
  min-width: 0;
  background: #f8fbff;
}

.chat-header {
  height: 66px;
  gap: 12px;
  padding: 0 24px;
  border-bottom: 1px solid #dce6f2;
  background: #fff;
}

.header-copy {
  min-width: 0;
}

.header-title {
  color: #0f172a;
  font-size: 17px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-subtitle {
  margin-top: 3px;
  color: #64748b;
  font-size: 13px;
}

.header-user {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #334155;
  flex-shrink: 0;
}

.mobile-menu {
  display: none;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 22px;
}

.empty-state {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  color: #64748b;
}

.empty-state h3 {
  margin: 14px 0 8px;
  color: #0f172a;
  font-size: 22px;
  font-weight: 700;
}

.scenario-grid {
  margin-top: 24px;
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.scenario-item {
  border: 1px solid #d7e2ee;
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  color: #334155;
  cursor: pointer;
  text-align: left;
  min-height: 56px;
  font-size: 14px;
}

.scenario-item:hover {
  border-color: #93c5fd;
  color: #1d4ed8;
}

.message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
  max-width: 88%;
}

.message-row.user {
  flex-direction: row-reverse;
  margin-left: auto;
}

.msg-avatar {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  font-size: 12px;
}

.user-avatar {
  color: #fff;
  background: #2563eb;
}

.ai-avatar {
  color: #fff;
  background: #059669;
}

.message-bubble {
  min-width: 0;
  max-width: 100%;
  background: #fff;
  padding: 12px 15px;
  border: 1px solid #dce6f2;
  border-radius: 8px;
  color: #1e293b;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.message-row.user .message-bubble {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.message-bubble :deep(p) {
  margin: 0 0 10px;
}

.message-bubble :deep(p:last-child) {
  margin-bottom: 0;
}

.message-bubble :deep(pre) {
  overflow-x: auto;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 10px;
}

.status-line,
.status-footer {
  gap: 8px;
  color: #64748b;
}

.status-footer {
  margin-top: 8px;
  font-size: 13px;
}

.input-area {
  padding: 14px 24px 18px;
  border-top: 1px solid #dce6f2;
  background: #fff;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-area :deep(.el-textarea) {
  flex: 1;
}

.send-btn {
  width: 96px;
  height: 40px;
}

:deep(.el-drawer__body) {
  padding: 0;
}

@media (max-width: 900px) {
  .login-page {
    padding: 18px;
  }

  .login-shell {
    min-height: 0;
    grid-template-columns: 1fr;
  }

  .login-hero {
    padding: 28px;
  }

  .hero-copy h2 {
    font-size: 28px;
  }

  .login-panel {
    padding: 30px 28px;
  }
}

@media (max-width: 768px) {
  .chat-container {
    padding: 0;
  }

  .app-shell {
    border: 0;
    border-radius: 0;
  }

  .desktop-sidebar {
    display: none;
  }

  .mobile-menu {
    display: inline-flex;
  }

  .chat-header {
    padding: 0 12px;
  }

  .header-subtitle,
  .header-user span {
    display: none;
  }

  .message-list {
    padding: 14px 12px;
  }

  .message-row {
    max-width: 100%;
  }

  .scenario-grid {
    grid-template-columns: 1fr;
  }

  .input-area {
    padding: 10px 12px 12px;
    flex-direction: column;
    align-items: stretch;
  }

  .send-btn {
    width: 100%;
  }
}
</style>



