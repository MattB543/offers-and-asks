<script setup lang="ts">
import type { AttendeeProfile } from '../types'

const props = defineProps<{
  profile: AttendeeProfile
  showMatchText?: boolean
}>()
</script>

<template>
  <div class="profile-card bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition">
    <!-- Header with name on left, job/country/score on right -->
    <div class="flex items-start justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">{{ profile.name }}</h3>
      <div class="text-right text-sm text-gray-600 ml-4">
        <span v-if="profile.job_title">{{ profile.job_title }}</span>
        <span v-if="profile.job_title && (profile.company || profile.country)"> • </span>
        <span v-if="profile.company">{{ profile.company }}</span>
        <span v-if="profile.company && profile.country"> • </span>
        <span v-if="profile.country">{{ profile.country }}</span>
        <span v-if="profile.job_title || profile.company || profile.country"> • </span>
        <span class="font-semibold text-gray-700">{{ Math.round(profile.similarity_score * 100) }}% Match Score</span>
      </div>
    </div>

    <!-- Match text (offering or request) -->
    <div v-if="showMatchText && profile.text" class="mb-4 p-3 bg-blue-50 rounded border-l-4 border-blue-600">
      <p class="text-sm text-gray-700">
        <span class="font-medium text-blue-700">Match: </span>
        {{ profile.text }}
      </p>
    </div>

    <!-- Biography (always shown) -->
    <div v-if="profile.biography" class="mb-4 text-sm text-gray-600 bg-gray-50 p-3 rounded">
      {{ profile.biography }}
    </div>

    <!-- Action buttons -->
    <div class="flex flex-wrap gap-2">
      <a
        v-if="profile.linkedin"
        :href="profile.linkedin"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200 transition no-underline"
      >
        <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
        </svg>
        LinkedIn
      </a>

      <a
        v-if="profile.swapcard"
        :href="profile.swapcard"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200 transition no-underline"
      >
        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
        </svg>
        Swapcard
      </a>
    </div>
  </div>
</template>

<style scoped>
.profile-card {
  transition: all 0.2s ease;
}

a {
  text-decoration: none !important;
}

.h-5 {
  height: 1.25rem;
}

.w-5 {
  width: 1.25rem;
}

.w-4 {
  width: 1rem;
}

.h-4 {
  height: 1rem;
}

.h-2 {
  height: 0.5rem;
}
</style>
