<script setup lang="ts">
import { RouterView, RouterLink } from 'vue-router'
</script>

<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-8">
            <RouterLink to="/" class="text-2xl font-bold text-gray-900 hover:text-blue-600 transition no-underline">
              EA Global Matching
            </RouterLink>
            <nav class="hidden md:flex space-x-6">
              <RouterLink
                to="/"
                class="text-gray-600 hover:text-gray-900 transition no-underline"
                active-class="text-blue-600 font-semibold"
              >
                Search
              </RouterLink>
              <RouterLink
                to="/about"
                class="text-gray-600 hover:text-gray-900 transition no-underline"
                active-class="text-blue-600 font-semibold"
              >
                About
              </RouterLink>
            </nav>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <RouterView />
    </main>
  </div>
</template>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a, .no-underline {
  text-decoration: none !important;
}
</style>
