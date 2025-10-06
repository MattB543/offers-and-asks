<script setup lang="ts">
defineProps<{
  message?: string
}>()
</script>

<template>
  <div class="loading-spinner">
    <div class="spinner"></div>
    <p v-if="message" class="loading-message">{{ message }}</p>
  </div>
</template>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f4f6;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-message {
  margin-top: 1rem;
  color: #6b7280;
  font-size: 0.875rem;
}
</style>
