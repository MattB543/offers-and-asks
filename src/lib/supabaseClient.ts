// Supabase client configuration
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing Supabase environment variables. ' +
    'Please ensure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set in your .env file.'
  )
}

/**
 * Custom fetch with configurable timeout
 * Workaround for hardcoded 60s timeout in @supabase/supabase-js
 * See: https://github.com/supabase/supabase-js/issues/1399
 */
const createFetchWithTimeout = (timeoutMs: number = 180000) => {
  return async (url: RequestInfo | URL, options?: RequestInit) => {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      return response
    } catch (error) {
      clearTimeout(timeoutId)
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout after ${timeoutMs}ms`)
      }
      throw error
    }
  }
}

// Create Supabase client with 3-minute timeout for Edge Functions
// This is necessary for username search which can take 2+ minutes with multiple LLM calls
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  global: {
    fetch: createFetchWithTimeout(180000) // 3 minutes (180 seconds)
  }
})
