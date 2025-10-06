// Composable for Supabase Edge Functions
import { ref, type Ref } from 'vue'
import { supabase } from '../lib/supabaseClient'
import type { UsernameSearchResult, SimpleSearchResult } from '../types'

export function useSupabase() {
  const loading = ref(false)
  const error: Ref<Error | null> = ref(null)

  async function searchByUsername(name: string): Promise<UsernameSearchResult | null> {
    loading.value = true
    error.value = null

    try {
      const { data, error: invokeError } = await supabase.functions.invoke('search-by-username', {
        body: { name },
      })

      if (invokeError) {
        throw invokeError
      }

      if (data?.error) {
        throw new Error(data.error)
      }

      return data as UsernameSearchResult
    } catch (err) {
      error.value = err as Error
      console.error('Search by username failed:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  async function searchByRequest(request: string): Promise<SimpleSearchResult | null> {
    loading.value = true
    error.value = null

    try {
      const { data, error: invokeError } = await supabase.functions.invoke('search-by-request', {
        body: { request },
      })

      if (invokeError) {
        throw invokeError
      }

      if (data?.error) {
        throw new Error(data.error)
      }

      return data as SimpleSearchResult
    } catch (err) {
      error.value = err as Error
      console.error('Search by request failed:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  async function searchByOffering(offering: string): Promise<SimpleSearchResult | null> {
    loading.value = true
    error.value = null

    try {
      const { data, error: invokeError } = await supabase.functions.invoke('search-by-offering', {
        body: { offering },
      })

      if (invokeError) {
        throw invokeError
      }

      if (data?.error) {
        throw new Error(data.error)
      }

      return data as SimpleSearchResult
    } catch (err) {
      error.value = err as Error
      console.error('Search by offering failed:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  async function getAttendees(): Promise<Array<{ id: number; value: string; label: string }> | null> {
    loading.value = true
    error.value = null

    try {
      const { data, error: invokeError } = await supabase.functions.invoke('get-attendees', {
        body: {},
      })

      if (invokeError) {
        throw invokeError
      }

      if (data?.error) {
        throw new Error(data.error)
      }

      return data as Array<{ id: number; value: string; label: string }>
    } catch (err) {
      error.value = err as Error
      console.error('Get attendees failed:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    searchByUsername,
    searchByRequest,
    searchByOffering,
    getAttendees,
  }
}
