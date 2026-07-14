import { expect, type Page, test } from '@playwright/test'

type User = { user_id: string; username: string; display_name: string }
type Session = { session_id: string; title: string; created_at: string; updated_at: string; last_message: string; message_count: number }
type Message = { id: number; role: 'user' | 'assistant'; content: string; created_at: string }
type AgentTrace = {
  trace_id: string
  user_id: string
  session_id: string
  query: string
  status: string
  route_agent: string
  stages: { status: string; message: string; at: string }[]
  duration_ms: number
  error_message: string | null
  created_at: string
  updated_at: string
}

const users: Record<string, User> = {
  user_1001: { user_id: 'user_1001', username: 'user_1001', display_name: 'User 1001' },
  user_1002: { user_id: 'user_1002', username: 'user_1002', display_name: 'User 1002' },
}

async function setupMockApi(page: Page) {
  const sessionsByUser: Record<string, Session[]> = { user_1001: [], user_1002: [] }
  const messagesBySession: Record<string, Message[]> = {}
  const tracesBySession: Record<string, AgentTrace[]> = {}
  let sessionCounter = 1
  let messageCounter = 1

  const userFromRequest = (request: { headers: () => Record<string, string> }) => {
    const auth = request.headers()['authorization'] || ''
    const username = auth.replace('Bearer access-', '')
    return users[username] || users.user_1001
  }

  await page.route('**/api/auth/login', async (route) => {
    const payload = route.request().postDataJSON() as { username: string; password: string }
    const user = users[payload.username]
    if (!user || payload.password !== 'Cloud@123456') {
      await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Invalid username or password' }) })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: `access-${user.username}`,
        refresh_token: `refresh-${user.username}`,
        token_type: 'bearer',
        expires_in: 1800,
        refresh_expires_at: new Date(Date.now() + 86400000).toISOString(),
        user,
      }),
    })
  })

  await page.route('**/api/auth/me', async (route) => {
    const user = userFromRequest(route.request())
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) })
  })

  await page.route('**/api/auth/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: 'access-user_1001', refresh_token: 'refresh-user_1001-new', token_type: 'bearer', expires_in: 1800, refresh_expires_at: new Date(Date.now() + 86400000).toISOString(), user: users.user_1001 }),
    })
  })

  await page.route('**/api/auth/logout', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) })
  })

  await page.route('**/api/sessions', async (route) => {
    const user = userFromRequest(route.request())
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(sessionsByUser[user.user_id]) })
      return
    }
    const createdAt = new Date().toISOString()
    const session: Session = {
      session_id: `session_${sessionCounter++}`,
      title: 'New Chat',
      created_at: createdAt,
      updated_at: createdAt,
      last_message: '',
      message_count: 0,
    }
    sessionsByUser[user.user_id].unshift(session)
    messagesBySession[session.session_id] = []
    tracesBySession[session.session_id] = []
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(session) })
  })

  await page.route('**/api/sessions/*/messages', async (route) => {
    const sessionId = route.request().url().match(/sessions\/(.+)\/messages/)?.[1] || ''
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(messagesBySession[sessionId] || []) })
  })

  await page.route('**/api/sessions/*/traces', async (route) => {
    const sessionId = route.request().url().match(/sessions\/(.+)\/traces/)?.[1] || ''
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(tracesBySession[sessionId] || []) })
  })

  await page.route('**/api/sessions/*', async (route) => {
    const user = userFromRequest(route.request())
    const sessionId = route.request().url().split('/').pop() || ''
    sessionsByUser[user.user_id] = sessionsByUser[user.user_id].filter((session) => session.session_id !== sessionId)
    delete messagesBySession[sessionId]
    delete tracesBySession[sessionId]
    await route.fulfill({ status: 204, body: '' })
  })

  await page.route('**/api/chat', async (route) => {
    const user = userFromRequest(route.request())
    const payload = route.request().postDataJSON() as { query: string; session_id: string }
    const session = sessionsByUser[user.user_id].find((item) => item.session_id === payload.session_id)
    const answer = 'Order found: ORD-1001-001, product ecs.g8a.4xlarge, status Paid.'
    const now = new Date().toISOString()

    messagesBySession[payload.session_id].push({ id: messageCounter++, role: 'user', content: payload.query, created_at: now })
    messagesBySession[payload.session_id].push({ id: messageCounter++, role: 'assistant', content: answer, created_at: now })
    tracesBySession[payload.session_id] = [{
      trace_id: `trace-${payload.session_id}`,
      user_id: user.user_id,
      session_id: payload.session_id,
      query: payload.query,
      status: 'success',
      route_agent: 'order_agent',
      stages: [
        { status: 'thinking', message: 'Thinking', at: now },
        { status: 'agent_routing', message: 'Routed to order_agent', at: now },
        { status: 'streaming', message: 'Streaming answer', at: now },
      ],
      duration_ms: 88,
      error_message: null,
      created_at: now,
      updated_at: now,
    }]
    if (session) {
      session.title = session.title === 'New Chat' ? payload.query.slice(0, 40) : session.title
      session.last_message = answer
      session.message_count = messagesBySession[payload.session_id].length
      session.updated_at = now
    }

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream; charset=utf-8',
      body: [
        'data: {"type":"status","status":"thinking","message":"Thinking"}\n\n',
        `data: ${JSON.stringify({ type: 'content', content: answer })}\n\n`,
        'data: {"type":"done","done":true}\n\n',
      ].join(''),
    })
  })
}

async function login(page: Page, username = 'user_1001') {
  const inputs = page.locator('.login-form input')
  await expect(inputs).toHaveCount(2)
  await inputs.nth(0).fill(username)
  await inputs.nth(1).fill('Cloud@123456')
  await page.locator('.login-button').click()
  await expect(page.locator('.chat-header')).toBeVisible()
}

test.beforeEach(async ({ page }) => {
  await setupMockApi(page)
})

test('desktop chat history lifecycle and trace drawer', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.login-shell')).toBeVisible()
  await expect(page.locator('.login-shell')).toHaveCSS('display', 'grid')

  await login(page)
  const scenarios = page.locator('.scenario-item')
  await expect(scenarios).toHaveCount(6)
  await scenarios.nth(1).click()
  await expect(page.getByText('ORD-1001-001')).toBeVisible()
  await expect(page.locator('.session-item')).toHaveCount(1)

  await page.locator('.header-user button[title="调用轨迹"]').click()
  await expect(page.getByText('订单查询 Agent')).toBeVisible()
  await expect(page.getByText('88 ms')).toBeVisible()
  await page.keyboard.press('Escape')

  await page.locator('.delete-session').click()
  await page.locator('.el-message-box__btns .el-button--primary').click()
  await expect(page.locator('.session-item')).toHaveCount(0)

  await page.locator('.header-user button[title="退出登录"]').click()
  await expect(page.locator('.login-button')).toBeVisible()
})

test('mobile layout uses drawer and has no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await login(page)

  await expect(page.locator('.desktop-sidebar')).toBeHidden()
  await expect(page.locator('.mobile-menu')).toBeVisible()
  await page.locator('.mobile-menu').click()
  await expect(page.locator('.mobile-drawer')).toBeVisible()

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
  await expect(page.locator('.input-area')).toBeVisible()
})

test('different users see isolated session lists', async ({ page }) => {
  await page.goto('/')
  await login(page, 'user_1001')
  const scenarios = page.locator('.scenario-item')
  await expect(scenarios).toHaveCount(6)
  await scenarios.nth(1).click()
  await expect(page.getByText('ORD-1001-001')).toBeVisible()

  await page.locator('.header-user button[title="退出登录"]').click()
  await login(page, 'user_1002')
  await expect(page.locator('.session-item')).toHaveCount(0)
})
