export type User = { id: number; username: string }
export type CampaignSummary = { id: number; name: string; is_game_master: boolean }
export type Item = { id: number; name: string; description: string; campaign_id: number | null; created_by_id: number | null; source_system: string | null; source_identifier: string | null; source_repository: string | null; is_imported: boolean }
export type Character = { id: number; name: string; is_active: boolean; race: string; class: string; experience: number; money: Record<string, number | string>; inventory: Array<{ item_id: number; name: string; quantity: number }> }
export type Campaign = CampaignSummary & { use_shared_exp: boolean; shared_experience: number; characters: Character[] }
export type LedgerEntry = { account_id: number; amount: number; item_id?: number; item_name?: string; denomination?: string }
export type LedgerTransaction = { id: number; ledger: string; description: string; created_at: string; entries: LedgerEntry[]; reversal_of_id: number | null; is_reversed: boolean; reason?: string; requested_amount?: number; discarded_amount?: number }

let csrfToken = ''

function getCookie(name: string): string {
  if (typeof document === 'undefined') return ''
  const cookie = document.cookie.split('; ').find((value) => value.startsWith(`${name}=`))
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : ''
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getCookie('csrftoken') || csrfToken
  const unsafe = !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(options.method ?? 'GET')
  const response = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(unsafe ? { 'X-CSRFToken': token } : {}),
      ...options.headers,
    },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error))
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

export async function initialiseCsrf(): Promise<void> {
  const response = await request<{ csrfToken: string }>('/api/auth/csrf/')
  csrfToken = getCookie('csrftoken') || response.csrfToken
}
export const getSession = () => request<User>('/api/auth/session/')
export const login = (username: string, password: string) => request<User>('/api/auth/login/', { method: 'POST', body: JSON.stringify({ username, password }) })
export const logout = () => request<void>('/api/auth/logout/', { method: 'POST' })
export const getCampaigns = () => request<CampaignSummary[]>('/api/campaigns/')
export const getCampaign = (id: number) => request<Campaign>(`/api/campaigns/${id}/`)
export const getItems = (id: number) => request<Item[]>(`/api/campaigns/${id}/items/`)
export const createItem = (id: number, name: string, description: string) => request<Item>(`/api/campaigns/${id}/items/`, { method: 'POST', body: JSON.stringify({ name, description }) })
export const copyItem = (campaignId: number, itemId: number, name: string, description: string) => request<Item>(`/api/campaigns/${campaignId}/items/${itemId}/copy/`, { method: 'POST', body: JSON.stringify({ name, description }) })
export const postAction = (campaignId: number, action: string, payload: object) => request(`/api/campaigns/${campaignId}/actions/${action}/`, { method: 'POST', body: JSON.stringify(payload) })
export const getTransactions = (campaignId: number, ledger = 'all', page = 1) => request<{ count: number; page: number; page_size: number; results: LedgerTransaction[] }>(`/api/campaigns/${campaignId}/transactions/?ledger=${ledger}&page=${page}`)
export const reverseTransaction = (campaignId: number, transaction: LedgerTransaction, description: string) => request(`/api/campaigns/${campaignId}/transactions/${transaction.ledger}/${transaction.id}/reverse/`, { method: 'POST', body: JSON.stringify({ description }) })
