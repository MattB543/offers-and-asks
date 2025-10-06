<script setup lang="ts">
import { ref } from 'vue'
import ProfileCard from './ProfileCard.vue'
import type { UsernameSearchResult, SimpleSearchResult } from '../types'

const props = defineProps<{
  usernameResult?: UsernameSearchResult | null
  simpleResult?: SimpleSearchResult | null
  searchType: 'username' | 'request' | 'offering'
}>()

const expandedSections = ref<Record<string, boolean>>({})

const toggleSection = (key: string) => {
  expandedSections.value[key] = !expandedSections.value[key]
}
</script>

<template>
  <div class="results-list">
    <!-- Username Search Results (Bidirectional) -->
    <div v-if="searchType === 'username' && usernameResult" class="space-y-8">
      <!-- Attendee Info Card -->
      <div class="attendee-info-card bg-white border-2 border-blue-200 rounded-lg p-6 shadow-sm">
        <div class="flex items-center mb-2">
          <svg class="w-6 h-6 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <h2 class="text-2xl font-bold text-gray-900">{{ usernameResult.attendee.name }}</h2>
        </div>
        <p class="text-gray-600">
          <span v-if="usernameResult.attendee.job_title">{{ usernameResult.attendee.job_title }}</span>
          <span v-if="usernameResult.attendee.job_title && usernameResult.attendee.company"> at </span>
          <span v-if="usernameResult.attendee.company" class="font-medium">{{ usernameResult.attendee.company }}</span>
        </p>
        <p v-if="usernameResult.attendee.country" class="text-gray-500 text-sm mt-1">
          {{ usernameResult.attendee.country }}
        </p>
      </div>

      <!-- People Who Can Help You -->
      <div
        v-if="usernameResult.people_who_can_help_you && usernameResult.people_who_can_help_you.length > 0"
        class="results-section"
      >
        <h3 class="text-xl font-bold text-gray-900 mb-4">
          People Who Can Help You
          <span class="text-sm font-medium text-gray-600 ml-2">
            ({{ usernameResult.people_who_can_help_you.length }} request{{ usernameResult.people_who_can_help_you.length !== 1 ? 's' : '' }})
          </span>
        </h3>

        <div class="space-y-6">
          <div
            v-for="(group, index) in usernameResult.people_who_can_help_you"
            :key="`help-${index}`"
            class="request-group"
          >
            <button
              @click="toggleSection(`help-${index}`)"
              class="w-full text-left p-4 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <p class="font-medium text-gray-900 mb-1">Your Request:</p>
                  <p class="text-gray-700">{{ group.your_request }}</p>
                  <p class="text-sm text-gray-500 mt-2">{{ group.matches.length }} matches found</p>
                </div>
                <svg
                  class="w-5 h-5 text-gray-400 transition-transform"
                  :class="{ 'rotate-180': expandedSections[`help-${index}`] }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            <div v-if="expandedSections[`help-${index}`]" class="mt-4 grid grid-cols-1 gap-4">
              <ProfileCard
                v-for="(profile, pIndex) in group.matches"
                :key="`help-${index}-${pIndex}`"
                :profile="profile"
                :show-match-text="true"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- People You Can Help -->
      <div
        v-if="usernameResult.people_you_can_help && usernameResult.people_you_can_help.length > 0"
        class="results-section"
      >
        <h3 class="text-xl font-bold text-gray-900 mb-4">
          People You Can Help
          <span class="text-sm font-medium text-gray-600 ml-2">
            ({{ usernameResult.people_you_can_help.length }} offering{{ usernameResult.people_you_can_help.length !== 1 ? 's' : '' }})
          </span>
        </h3>

        <div class="space-y-6">
          <div
            v-for="(group, index) in usernameResult.people_you_can_help"
            :key="`offering-${index}`"
            class="offering-group"
          >
            <button
              @click="toggleSection(`offering-${index}`)"
              class="w-full text-left p-4 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <p class="font-medium text-gray-900 mb-1">Your Offering:</p>
                  <p class="text-gray-700">{{ group.your_offering }}</p>
                  <p class="text-sm text-gray-500 mt-2">{{ group.matches.length }} matches found</p>
                </div>
                <svg
                  class="w-5 h-5 text-gray-400 transition-transform"
                  :class="{ 'rotate-180': expandedSections[`offering-${index}`] }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            <div v-if="expandedSections[`offering-${index}`]" class="mt-4 grid grid-cols-1 gap-4">
              <ProfileCard
                v-for="(profile, pIndex) in group.matches"
                :key="`offering-${index}-${pIndex}`"
                :profile="profile"
                :show-match-text="true"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Simple Search Results (Request/Offering) -->
    <div v-if="(searchType === 'request' || searchType === 'offering') && simpleResult" class="space-y-6">
      <!-- Results Header -->
      <div class="results-header bg-white border-l-4 border-blue-600 rounded-lg p-6 shadow-sm">
        <div class="flex items-center mb-3">
          <svg class="w-6 h-6 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h2 class="text-2xl font-bold text-gray-900">
            {{ searchType === 'request' ? 'People Who Can Help' : 'People You Can Help' }}
          </h2>
        </div>
        <p class="text-gray-700 mb-2">
          <span class="font-medium">Your {{ searchType }}:</span> {{ simpleResult.query }}
        </p>
        <p class="text-sm text-gray-600">
          {{ simpleResult.matches.length }} match{{ simpleResult.matches.length !== 1 ? 'es' : '' }} found
        </p>
      </div>

      <!-- Results Grid -->
      <div class="grid grid-cols-1 gap-4">
        <ProfileCard
          v-for="(profile, index) in simpleResult.matches"
          :key="index"
          :profile="profile"
          :show-match-text="true"
        />
      </div>
    </div>

    <!-- No Results State -->
    <div v-if="!usernameResult && !simpleResult" class="no-results text-center py-12">
      <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="text-gray-500 text-lg">No results to display</p>
      <p class="text-gray-400 text-sm mt-2">Try searching for an attendee or enter a request/offering</p>
    </div>
  </div>
</template>

<style scoped>
.results-list {
  margin-top: 2rem;
}

.w-6 {
  width: 1.5rem;
}

.h-6 {
  height: 1.5rem;
}

.w-5 {
  width: 1.25rem;
}

.h-5 {
  height: 1.25rem;
}

.w-16 {
  width: 4rem;
}

.h-16 {
  height: 4rem;
}

.mr-2 {
  margin-right: 0.5rem;
}

.rotate-180 {
  transform: rotate(180deg);
}

@media (min-width: 768px) {
  .grid-cols-1 {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}
</style>
