<script setup lang="ts">
import { ref } from "vue";
import SearchBar from "../components/SearchBar.vue";
import ResultsList from "../components/ResultsList.vue";
import LoadingSpinner from "../components/LoadingSpinner.vue";
import { useSupabase } from "../composables/useSupabase";
import type {
  SearchMode,
  UsernameSearchResult,
  SimpleSearchResult,
} from "../types";

const { loading, error, searchByUsername, searchByRequest, searchByOffering } =
  useSupabase();

const currentSearchType = ref<SearchMode | null>(null);
const usernameResult = ref<UsernameSearchResult | null>(null);
const simpleResult = ref<SimpleSearchResult | null>(null);
const hasSearched = ref(false);

const handleSearch = async (query: string, mode: SearchMode) => {
  // Reset previous results
  usernameResult.value = null;
  simpleResult.value = null;
  currentSearchType.value = mode;
  hasSearched.value = true;

  if (mode === "username") {
    const result = await searchByUsername(query);
    if (result) {
      usernameResult.value = result;
    }
  } else if (mode === "request") {
    const result = await searchByRequest(query);
    if (result) {
      simpleResult.value = result;
    }
  } else if (mode === "offering") {
    const result = await searchByOffering(query);
    if (result) {
      simpleResult.value = result;
    }
  }
};
</script>

<template>
  <div class="search-view">
    <!-- Page Header -->
    <div class="page-header mb-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-1">
        Find Your Connections
      </h1>
      <p class="text-gray-600">
        Search by name, describe what you need, or share what you can offer to
        find the perfect match.
      </p>
    </div>

    <!-- Search Bar -->
    <SearchBar @search="handleSearch" />

    <!-- Loading State -->
    <div v-if="loading" class="mt-8">
      <LoadingSpinner
        :message="currentSearchType === 'username'
          ? 'Analyzing attendee profile and finding matches... This may take 1-2 minutes.'
          : 'Searching for matches...'"
      />
    </div>

    <!-- Error State -->
    <div v-else-if="error && hasSearched" class="mt-8">
      <div
        class="error-card bg-red-50 border-l-4 border-red-500 p-6 rounded-lg"
      >
        <div class="flex items-start">
          <svg
            class="w-6 h-6 text-red-500 mr-3 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <h3 class="text-lg font-semibold text-red-800 mb-1">
              Search Error
            </h3>
            <p class="text-red-700">{{ error.message }}</p>
            <p class="text-sm text-red-600 mt-2">
              Please try again or contact support if the problem persists.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Results -->
    <div v-else-if="!loading && hasSearched">
      <ResultsList
        :username-result="usernameResult"
        :simple-result="simpleResult"
        :search-type="currentSearchType || 'username'"
      />
    </div>

    <!-- Welcome State (Before First Search) -->
    <div v-else class="welcome-state mt-4">
      <div class="text-center py-12">
        <h2 class="text-2xl font-bold text-gray-800 mb-3">Start Your Search</h2>
        <p class="text-gray-600 max-w-2xl mx-auto">
          Use the search bar above to find connections at EA Global. You can
          search by attendee name, describe what you're looking for, or share
          what you can offer to help others.
        </p>

        <div
          class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 max-w-4xl mx-auto text-left"
        >
          <!-- Username Search Card -->
          <div
            class="feature-card bg-white p-6 rounded-lg border border-gray-200 shadow-sm"
          >
            <div
              class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4"
            >
              <svg
                class="w-6 h-6 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
            </div>
            <h3 class="font-semibold text-gray-900 mb-2">Search by Name</h3>
            <p class="text-sm text-gray-600">
              Find an attendee and see bidirectional matches: who can help them
              and who they can help.
            </p>
          </div>

          <!-- Request Search Card -->
          <div
            class="feature-card bg-white p-6 rounded-lg border border-gray-200 shadow-sm"
          >
            <div
              class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4"
            >
              <svg
                class="w-6 h-6 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
            <h3 class="font-semibold text-gray-900 mb-2">Search by Request</h3>
            <p class="text-sm text-gray-600">
              Describe what you need help with and find people who can offer
              relevant expertise.
            </p>
          </div>

          <!-- Offering Search Card -->
          <div
            class="feature-card bg-white p-6 rounded-lg border border-gray-200 shadow-sm"
          >
            <div
              class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4"
            >
              <svg
                class="w-6 h-6 text-purple-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                />
              </svg>
            </div>
            <h3 class="font-semibold text-gray-900 mb-2">Search by Offering</h3>
            <p class="text-sm text-gray-600">
              Share what you can offer and discover people who are looking for
              your specific skills.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-view {
  max-width: 1200px;
  margin: 0 auto;
}

.w-6 {
  width: 1.5rem;
}

.h-6 {
  height: 1.5rem;
}

.w-12 {
  width: 3rem;
}

.h-12 {
  height: 3rem;
}

.w-20 {
  width: 5rem;
}

.h-20 {
  height: 5rem;
}

.mr-3 {
  margin-right: 0.75rem;
}

.flex-shrink-0 {
  flex-shrink: 0;
}

.feature-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.feature-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

@media (min-width: 768px) {
  .md\:grid-cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
