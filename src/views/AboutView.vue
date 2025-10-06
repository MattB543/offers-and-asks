<script setup lang="ts">
// About page for EA Global Matching
</script>

<template>
  <div class="about-view max-w-4xl mx-auto">
    <!-- Hero Section -->
    <div class="hero-section text-center mb-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">EA Global Matching</h1>
      <p class="text-xl text-gray-600">
        AI-powered semantic search to connect attendees with complementary
        skills and needs
      </p>
    </div>

    <!-- How It Works Section -->
    <section
      class="content-section bg-white rounded-lg shadow-sm p-8 mb-8 mt-10"
    >
      <h2 class="text-2xl font-bold text-gray-900 mb-6">How It Works</h2>

      <div class="space-y-6">
        <div class="step-card flex items-start">
          <div class="step-number flex-shrink-0">
            <div
              class="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold"
            >
              1
            </div>
          </div>
          <div class="ml-4 flex-1">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              Data Extraction
            </h3>
            <p class="text-gray-600">
              We analyze attendee profiles using Google's Gemini 2.5 Pro to
              extract structured offerings (what people can provide) and
              requests (what people need help with) from unstructured text.
            </p>
          </div>
        </div>

        <div class="step-card flex items-start">
          <div class="step-number flex-shrink-0">
            <div
              class="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold"
            >
              2
            </div>
          </div>
          <div class="ml-4 flex-1">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              Semantic Embeddings
            </h3>
            <p class="text-gray-600">
              Each offering and request is converted into a 1536-dimensional
              vector embedding using Gemini's embedding model. These vectors
              capture semantic meaning, enabling similarity search.
            </p>
          </div>
        </div>

        <div class="step-card flex items-start">
          <div class="step-number flex-shrink-0">
            <div
              class="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold"
            >
              3
            </div>
          </div>
          <div class="ml-4 flex-1">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              Hybrid Matching
            </h3>
            <p class="text-gray-600">
              We use a two-stage approach: first, fast vector similarity search
              finds the top 50 candidates; then, LLM re-ranking evaluates
              quality to return the final top 25 matches.
            </p>
          </div>
        </div>

        <div class="step-card flex items-start">
          <div class="step-number flex-shrink-0">
            <div
              class="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold"
            >
              4
            </div>
          </div>
          <div class="ml-4 flex-1">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              Real-time Search
            </h3>
            <p class="text-gray-600">
              Search by attendee name for bidirectional matches, or search by
              custom request/offering to find relevant connections in real-time.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Search Modes Section -->
    <section class="content-section bg-white rounded-lg shadow-sm p-8 mb-8">
      <h2 class="text-2xl font-bold text-gray-900 mb-6">Search Modes</h2>

      <div class="space-y-4">
        <div
          class="mode-card bg-blue-50 border-l-4 border-blue-600 p-4 rounded"
        >
          <h3 class="font-semibold text-blue-900 mb-2">Username Search</h3>
          <p class="text-blue-800 text-sm">
            Find an attendee by name to see bidirectional matches: who can help
            them (based on their requests) and who they can help (based on their
            offerings). Perfect for facilitating introductions.
          </p>
        </div>

        <div
          class="mode-card bg-green-50 border-l-4 border-green-600 p-4 rounded"
        >
          <h3 class="font-semibold text-green-900 mb-2">Request Search</h3>
          <p class="text-green-800 text-sm">
            Describe what you need help with in natural language. The system
            converts your request into a synthetic offering and finds people
            whose offerings match your need. Great for finding mentors,
            advisors, or collaborators.
          </p>
        </div>

        <div
          class="mode-card bg-purple-50 border-l-4 border-purple-600 p-4 rounded"
        >
          <h3 class="font-semibold text-purple-900 mb-2">Offering Search</h3>
          <p class="text-purple-800 text-sm">
            Share what you can offer or teach. The system finds people whose
            requests match your offering. Ideal for discovering who you can help
            or mentor at the conference.
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.about-view {
  padding: 2rem 0;
}

.content-section {
  margin-bottom: 2rem;
}

.w-10 {
  width: 2.5rem;
}

.h-10 {
  height: 2.5rem;
}

.ml-4 {
  margin-left: 1rem;
}

.space-y-1 > * + * {
  margin-top: 0.25rem;
}

@media (min-width: 768px) {
  .md\:grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .md\:grid-cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
