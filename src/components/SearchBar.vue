<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSupabase } from '../composables/useSupabase'
import type { SearchMode } from '../types'

const emit = defineEmits<{
  search: [query: string, mode: SearchMode]
}>()

const { getAttendees } = useSupabase()

const searchQuery = ref('')
const searchMode = ref<SearchMode>('username')
const attendees = ref<Array<{ id: number; value: string; label: string }>>([])
const filteredAttendees = ref<Array<{ id: number; value: string; label: string }>>([])
const showDropdown = ref(false)
const loadingAttendees = ref(false)

const placeholder = computed(() => {
  switch (searchMode.value) {
    case 'username':
      return 'Select an attendee...'
    case 'request':
      return 'I need help with AI safety research...'
    case 'offering':
      return 'I can provide mentorship on community building...'
  }
})

const isSearchDisabled = computed(() => {
  return searchQuery.value.trim().length === 0
})

const handleSearch = () => {
  if (!isSearchDisabled.value) {
    emit('search', searchQuery.value.trim(), searchMode.value)
  }
}

const setMode = (mode: SearchMode) => {
  searchMode.value = mode
  searchQuery.value = ''
  showDropdown.value = false
}

const filterAttendees = () => {
  const query = searchQuery.value.toLowerCase()
  if (query.length === 0) {
    filteredAttendees.value = attendees.value.slice(0, 50) // Show first 50 by default
  } else {
    filteredAttendees.value = attendees.value
      .filter(att => att.value.toLowerCase().includes(query))
      .slice(0, 50) // Limit to 50 results
  }
}

const handleInputFocus = () => {
  if (searchMode.value === 'username') {
    filterAttendees()
    showDropdown.value = true
  }
}

const handleInputChange = () => {
  if (searchMode.value === 'username') {
    filterAttendees()
    showDropdown.value = true
  }
}

const selectAttendee = (attendee: { id: number; value: string; label: string }) => {
  searchQuery.value = attendee.value
  showDropdown.value = false
}

const hideDropdown = () => {
  // Delay to allow click events on dropdown items to fire
  setTimeout(() => {
    showDropdown.value = false
  }, 200)
}

onMounted(async () => {
  loadingAttendees.value = true
  const result = await getAttendees()
  if (result) {
    attendees.value = result
    filteredAttendees.value = result.slice(0, 50) // Show first 50 by default
  }
  loadingAttendees.value = false
})
</script>

<template>
  <div class="search-bar">
    <!-- Mode Toggle Tabs -->
    <div class="mode-tabs mb-6">
      <button
        @click="setMode('username')"
        :class="[
          'mode-tab',
          searchMode === 'username' ? 'mode-tab-active' : 'mode-tab-inactive'
        ]"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
        Username
      </button>

      <button
        @click="setMode('request')"
        :class="[
          'mode-tab',
          searchMode === 'request' ? 'mode-tab-active' : 'mode-tab-inactive'
        ]"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        Request
      </button>

      <button
        @click="setMode('offering')"
        :class="[
          'mode-tab',
          searchMode === 'offering' ? 'mode-tab-active' : 'mode-tab-inactive'
        ]"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
        Offering
      </button>
    </div>

    <!-- Search Input -->
    <div class="search-input-container" style="position: relative;">
      <input
        v-model="searchQuery"
        type="text"
        :placeholder="placeholder"
        @keydown.enter="handleSearch"
        @focus="handleInputFocus"
        @input="handleInputChange"
        @blur="hideDropdown"
        class="search-input"
        :disabled="searchMode === 'username' && loadingAttendees"
      />

      <!-- Dropdown for username mode -->
      <div
        v-if="searchMode === 'username' && showDropdown && filteredAttendees.length > 0"
        class="attendee-dropdown"
      >
        <div
          v-for="attendee in filteredAttendees"
          :key="attendee.id"
          @mousedown="selectAttendee(attendee)"
          class="attendee-option"
        >
          {{ attendee.label }}
        </div>
      </div>

      <button
        @click="handleSearch"
        :disabled="isSearchDisabled || (searchMode === 'username' && loadingAttendees)"
        class="search-button"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </button>
    </div>

    <!-- Mode description -->
    <div class="mt-3 text-sm text-gray-600">
      <p v-if="searchMode === 'username'">
        Search for an attendee by name to see who can help them and who they can help.
      </p>
      <p v-else-if="searchMode === 'request'">
        Describe what you need help with, and we'll find people who can help.
      </p>
      <p v-else>
        Describe what you can offer, and we'll find people who need your help.
      </p>
    </div>
  </div>
</template>

<style scoped>
.search-bar {
  background: white;
  border-radius: 0.5rem;
  padding: 2rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}

.mode-tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
}

.mode-tab {
  display: flex;
  align-items: center;
  padding: 0.75rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  border: none;
  background: none;
  cursor: pointer;
  transition: all 150ms;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
}

.mode-tab-active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  background-color: #eff6ff;
}

.mode-tab-inactive {
  color: #6b7280;
}

.mode-tab-inactive:hover {
  color: #111827;
  background-color: #f9fafb;
}

.search-input-container {
  display: flex;
  gap: 0.5rem;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 1rem;
  transition: all 150ms;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.search-button {
  padding: 0.75rem 1.5rem;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-button:hover:not(:disabled) {
  background-color: #1d4ed8;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.search-button:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.w-5 {
  width: 1.25rem;
}

.h-5 {
  height: 1.25rem;
}

.mr-2 {
  margin-right: 0.5rem;
}

.attendee-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 4rem;
  max-height: 300px;
  overflow-y: auto;
  background: white;
  border: 2px solid #d1d5db;
  border-top: none;
  border-radius: 0 0 0.5rem 0.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  margin-top: -2px;
}

.attendee-option {
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background-color 150ms;
}

.attendee-option:hover {
  background-color: #eff6ff;
  color: #3b82f6;
}

.attendee-option:not(:last-child) {
  border-bottom: 1px solid #f3f4f6;
}
</style>
