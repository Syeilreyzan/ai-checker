<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-indigo-500 selection:text-white">
    <!-- Top Executive Navigation -->
    <header class="border-b border-slate-800/80 bg-slate-900/75 backdrop-blur sticky top-0 z-30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 font-bold text-lg">
            V
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-lg font-bold tracking-tight text-white">VeriText AI</h1>
              <span class="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                Executive PoC
              </span>
            </div>
            <p class="text-xs text-slate-400">
              Module 1: Forensic AI Origin Detector &bull; Module 2: Interactive Sentence Humanizer
            </p>
          </div>
        </div>

        <!-- Engine Status & API Settings Button -->
        <div class="flex items-center gap-3">
          <div
            class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs"
            :class="isLiveLlm ? 'bg-emerald-950/40 border-emerald-700/50 text-emerald-300' : 'bg-amber-950/40 border-amber-700/50 text-amber-300'"
          >
            <span
              class="w-2 h-2 rounded-full animate-pulse"
              :class="isLiveLlm ? 'bg-emerald-400' : 'bg-amber-400'"
            ></span>
            <span>
              Engine:
              <strong class="font-semibold uppercase">{{ activeProviderLabel }}</strong>
            </span>
          </div>

          <button
            @click="showSettingsModal = true"
            class="px-3.5 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
          >
            <span>⚙️ LLM API Config</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <!-- Quick Demo Samples Bar for CEO -->
      <section class="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div class="text-xs font-semibold uppercase tracking-wider text-indigo-400 mb-0.5">
            One-Click CEO Demo Scenarios
          </div>
          <p class="text-xs text-slate-400">
            Load a sample document to test AI detection and interactive sentence-by-sentence humanization:
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-for="sample in samples"
            :key="sample.id"
            @click="loadSample(sample)"
            class="px-3.5 py-2 rounded-xl text-xs font-medium border transition flex items-center gap-2"
            :class="
              activeSampleId === sample.id
                ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200 shadow-sm'
                : 'bg-slate-800/70 hover:bg-slate-800 border-slate-700/80 text-slate-300'
            "
          >
            <span>{{ sample.title }}</span>
            <span
              class="px-1.5 py-0.5 text-[10px] rounded font-semibold"
              :class="
                sample.id === 'ai-corporate'
                  ? 'bg-rose-500/20 text-rose-300'
                  : sample.id === 'mixed-report'
                  ? 'bg-amber-500/20 text-amber-300'
                  : 'bg-emerald-500/20 text-emerald-300'
              "
            >
              {{ sample.badge }}
            </span>
          </button>
        </div>
      </section>

      <!-- Workspace Grid: Left Document Inspector / Editor + Right Analytics & Interactive Correction Queue -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <!-- LEFT COLUMN (7 cols): Text Input & Interactive Highlighted Document -->
        <div class="lg:col-span-7 space-y-4">
          <div class="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <!-- Toolbar -->
            <div class="px-5 py-3.5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-900/60">
              <div class="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
                <button
                  @click="viewMode = 'inspector'"
                  :disabled="!analysisResult"
                  class="px-3 py-1.5 rounded-lg text-xs font-medium transition"
                  :class="
                    viewMode === 'inspector'
                      ? 'bg-indigo-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                  "
                >
                  🔍 Interactive Sentence Inspector
                </button>
                <button
                  @click="viewMode = 'editor'"
                  class="px-3 py-1.5 rounded-lg text-xs font-medium transition"
                  :class="
                    viewMode === 'editor'
                      ? 'bg-indigo-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  "
                >
                  ✏️ Raw Text Editor
                </button>
              </div>

              <div class="flex items-center gap-2">
                <button
                  @click="copyCurrentText"
                  class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                >
                  {{ copied ? '✓ Copied!' : '📋 Copy Text' }}
                </button>
                <button
                  @click="runAnalysis"
                  :disabled="isAnalyzing || !inputText.trim()"
                  class="px-4 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white shadow-lg shadow-indigo-500/20 disabled:opacity-50 transition flex items-center gap-1.5"
                >
                  <span v-if="isAnalyzing" class="animate-spin">⏳</span>
                  <span>{{ isAnalyzing ? 'Scanning Document...' : '⚡ Scan for AI Origin' }}</span>
                </button>
              </div>
            </div>

            <!-- Mode 1: Raw Text Editor -->
            <div v-if="viewMode === 'editor' || !analysisResult" class="p-5">
              <textarea
                v-model="inputText"
                rows="12"
                placeholder="Paste or type any article, email, or report here to check for AI origin and humanize flagged sentences..."
                class="w-full bg-slate-950/90 border border-slate-800 rounded-xl p-4 text-sm leading-relaxed text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition resize-y"
              ></textarea>
              <div class="mt-3 flex items-center justify-between text-xs text-slate-400">
                <span>{{ wordCount }} words &bull; {{ characterCount }} characters</span>
                <span>Click <strong class="text-indigo-400">Scan for AI Origin</strong> to highlight AI sentences</span>
              </div>
            </div>

            <!-- Mode 2: Interactive Sentence-by-Sentence Highlighted Document -->
            <div v-else class="p-5 space-y-5">
              <!-- Highlight Color Legend -->
              <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800/80 text-xs">
                <div class="flex flex-wrap items-center gap-3">
                  <span class="flex items-center gap-1.5 text-slate-300">
                    <span class="w-3 h-3 rounded bg-rose-500/30 border border-rose-500"></span>
                    High AI (&ge;65%)
                  </span>
                  <span class="flex items-center gap-1.5 text-slate-300">
                    <span class="w-3 h-3 rounded bg-amber-500/30 border border-amber-500"></span>
                    Mixed AI (40–64%)
                  </span>
                  <span class="flex items-center gap-1.5 text-slate-300">
                    <span class="w-3 h-3 rounded bg-emerald-500/30 border border-emerald-500"></span>
                    Human / Corrected
                  </span>
                </div>
                <span class="text-slate-400 italic">Click any sentence below to inspect or humanize</span>
              </div>

              <!-- Interactive Sentences Paragraph -->
              <div class="p-4 rounded-xl bg-slate-950/90 border border-slate-800/90 leading-8 text-[15px] space-x-1">
                <span
                  v-for="sent in sentences"
                  :key="sent.id"
                  @click="selectSentence(sent.id)"
                  class="cursor-pointer rounded px-1.5 py-0.5 transition duration-150 inline"
                  :class="getSentenceHighlightClass(sent)"
                >
                  <span>{{ sent.text }}</span>
                  <sup
                    v-if="sent.accepted"
                    class="ml-1 text-[10px] font-bold text-emerald-300 bg-emerald-950/90 px-1 py-0.2 rounded"
                  >
                    ✓ Fixed
                  </sup>
                  <sup
                    v-else-if="sent.status !== 'human'"
                    class="ml-1 text-[10px] font-bold px-1 rounded"
                    :class="sent.status === 'ai' ? 'text-rose-300 bg-rose-950/90' : 'text-amber-300 bg-amber-950/90'"
                  >
                    {{ sent.ai_probability }}% AI
                  </sup>
                </span>
              </div>

              <!-- Selected Sentence Quick Inspector Banner inside Left Panel -->
              <div
                v-if="selectedSentence"
                class="rounded-xl border p-4 transition-all"
                :class="
                  selectedSentence.accepted
                    ? 'bg-emerald-950/20 border-emerald-700/50'
                    : selectedSentence.status === 'ai'
                    ? 'bg-rose-950/25 border-rose-700/50'
                    : selectedSentence.status === 'mixed'
                    ? 'bg-amber-950/25 border-amber-700/50'
                    : 'bg-slate-900 border-slate-800'
                "
              >
                <div class="flex items-center justify-between gap-2 mb-2">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Sentence #{{ selectedSentence.id + 1 }} Diagnostic
                    </span>
                    <span
                      class="text-xs font-semibold px-2 py-0.5 rounded-full"
                      :class="
                        selectedSentence.accepted
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          : selectedSentence.status === 'ai'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                          : selectedSentence.status === 'mixed'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                      "
                    >
                      {{
                        selectedSentence.accepted
                          ? '✓ Corrected to Human (8% AI)'
                          : `${selectedSentence.ai_probability}% AI Probability`
                      }}
                    </span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <button
                      v-if="selectedSentence.accepted && selectedSentence.text !== selectedSentence.original_text"
                      @click="revertSentence(selectedSentence)"
                      class="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    >
                      ↩ Revert to Original
                    </button>
                  </div>
                </div>

                <p class="text-sm text-white font-medium mb-2">"{{ selectedSentence.text }}"</p>

                <!-- Forensic Reasons -->
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span
                    v-for="(reason, rIdx) in selectedSentence.reasons"
                    :key="rIdx"
                    class="text-xs px-2.5 py-1 rounded-md bg-slate-900/90 border border-slate-700/80 text-slate-300"
                  >
                    🔎 {{ reason }}
                  </span>
                </div>

                <!-- Interactive Rewrite Suggestions for Selected Sentence -->
                <div v-if="selectedSentence.status !== 'human' || selectedSentence.suggestions?.length" class="space-y-2.5 pt-2 border-t border-slate-800/80">
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <span class="text-xs font-semibold text-indigo-300 uppercase tracking-wider">
                      ✨ Module 2: Choose a Human Correction or Edit
                    </span>
                    <div class="flex items-center gap-1.5">
                      <button
                        @click="regenerateSentenceSuggestions(selectedSentence)"
                        :disabled="regeneratingId === selectedSentence.id"
                        class="text-xs px-2.5 py-1 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-300 border border-indigo-500/30 transition"
                      >
                        {{ regeneratingId === selectedSentence.id ? '⏳ Generating...' : '🔄 Regenerate Options' }}
                      </button>
                      <button
                        @click="openManualEdit(selectedSentence)"
                        class="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                      >
                        ✏️ Edit Manually
                      </button>
                      <button
                        v-if="!selectedSentence.accepted"
                        @click="dismissSentenceFlag(selectedSentence)"
                        class="text-xs px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition"
                      >
                        Keep Original
                      </button>
                    </div>
                  </div>

                  <!-- Manual Edit Input Box -->
                  <div v-if="editingSentenceId === selectedSentence.id" class="p-3 rounded-xl bg-slate-950 border border-indigo-500/50 space-y-2">
                    <label class="block text-xs text-indigo-300 font-medium">Write your custom human revision:</label>
                    <textarea
                      v-model="manualEditText"
                      rows="2"
                      class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                    ></textarea>
                    <div class="flex justify-end gap-2">
                      <button
                        @click="editingSentenceId = null"
                        class="px-3 py-1 rounded-lg text-xs bg-slate-800 text-slate-300"
                      >
                        Cancel
                      </button>
                      <button
                        @click="applyRewrite(selectedSentence, manualEditText)"
                        class="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                      >
                        ✓ Apply Custom Edit
                      </button>
                    </div>
                  </div>

                  <!-- 3 Interactive Suggestion Cards -->
                  <div class="grid grid-cols-1 gap-2">
                    <div
                      v-for="(sug, sIdx) in selectedSentence.suggestions"
                      :key="sIdx"
                      class="p-3 rounded-xl bg-slate-950/90 border border-slate-800 hover:border-indigo-500/60 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div class="space-y-1">
                        <span class="inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300">
                          {{ sug.label }}
                        </span>
                        <p class="text-sm text-slate-100 leading-relaxed">{{ sug.text }}</p>
                      </div>
                      <button
                        @click="applyRewrite(selectedSentence, sug.text)"
                        class="shrink-0 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition"
                        :class="
                          selectedSentence.text === sug.text
                            ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40'
                            : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm'
                        "
                      >
                        {{ selectedSentence.text === sug.text ? '✓ Applied' : 'Accept Fix' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- RIGHT COLUMN (5 cols): AI Score Gauge, Before/After Impact, & Sentence Correction Queue -->
        <div class="lg:col-span-5 space-y-4">
          <!-- Overall AI Score & Live Correction Impact Card -->
          <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-sm font-bold uppercase tracking-wider text-slate-300">
                  AI Origin Assessment
                </h2>
                <p class="text-xs text-slate-400">
                  Live score recalculates as you accept sentence corrections
                </p>
              </div>
              <span
                v-if="analysisResult"
                class="px-3 py-1 rounded-full text-xs font-bold border"
                :class="
                  liveAiScore >= 65
                    ? 'bg-rose-500/15 text-rose-300 border-rose-500/40'
                    : liveAiScore >= 40
                    ? 'bg-amber-500/15 text-amber-300 border-amber-500/40'
                    : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
                "
              >
                {{ liveVerdict }}
              </span>
            </div>

            <!-- Score Bar + Before/After Comparison -->
            <div v-if="analysisResult" class="space-y-4">
              <div class="grid grid-cols-2 gap-3">
                <div class="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div class="text-xs text-slate-400 mb-1">Current AI Probability</div>
                  <div
                    class="text-3xl font-extrabold"
                    :class="
                      liveAiScore >= 65
                        ? 'text-rose-400'
                        : liveAiScore >= 40
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    "
                  >
                    {{ liveAiScore }}%
                  </div>
                  <div class="text-[11px] text-slate-400 mt-1">
                    {{ 100 - liveAiScore }}% Authentic Human Score
                  </div>
                </div>

                <div class="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div class="text-xs text-slate-400 mb-1">Correction Impact</div>
                  <div class="flex items-baseline gap-2">
                    <span class="text-3xl font-extrabold text-indigo-400">
                      {{ acceptedCount }}/{{ totalFlaggedCount }}
                    </span>
                    <span class="text-xs text-slate-400">sentences fixed</span>
                  </div>
                  <div class="text-[11px] mt-1" :class="scoreReduction > 0 ? 'text-emerald-400' : 'text-slate-400'">
                    <template v-if="scoreReduction > 0">
                      ↓ Reduced AI score by <strong>{{ scoreReduction }}%</strong> (from {{ initialAiScore }}%)
                    </template>
                    <template v-else>
                      Initial scan score: {{ initialAiScore }}% AI
                    </template>
                  </div>
                </div>
              </div>

              <!-- Visual Progress Meter -->
              <div class="space-y-1.5">
                <div class="flex justify-between text-xs font-medium">
                  <span class="text-emerald-400">Human ({{ 100 - liveAiScore }}%)</span>
                  <span class="text-rose-400">AI ({{ liveAiScore }}%)</span>
                </div>
                <div class="w-full h-3 rounded-full bg-slate-800 overflow-hidden flex">
                  <div
                    class="bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-500"
                    :style="{ width: `${100 - liveAiScore}%` }"
                  ></div>
                  <div
                    class="bg-gradient-to-r from-amber-500 to-rose-500 transition-all duration-500"
                    :style="{ width: `${liveAiScore}%` }"
                  ></div>
                </div>
              </div>

              <!-- Executive Summary -->
              <p class="text-xs text-slate-300 bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 leading-relaxed">
                {{ analysisResult.summary }}
              </p>

              <!-- 4 Linguistic Metrics Grid -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
                <div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80 text-center">
                  <div class="text-[11px] text-slate-400">Burstiness</div>
                  <div class="text-base font-bold text-slate-100 mt-0.5">
                    {{ analysisResult.metrics?.burstiness_score ?? 0 }}/100
                  </div>
                </div>
                <div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80 text-center">
                  <div class="text-[11px] text-slate-400">Uniformity</div>
                  <div class="text-base font-bold text-slate-100 mt-0.5">
                    {{ analysisResult.metrics?.uniformity_score ?? 0 }}%
                  </div>
                </div>
                <div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80 text-center">
                  <div class="text-[11px] text-slate-400">Vocab Richness</div>
                  <div class="text-base font-bold text-slate-100 mt-0.5">
                    {{ analysisResult.metrics?.vocabulary_richness ?? 0 }}/100
                  </div>
                </div>
                <div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80 text-center">
                  <div class="text-[11px] text-slate-400">AI Clichés</div>
                  <div class="text-base font-bold text-rose-400 mt-0.5">
                    {{ analysisResult.metrics?.cliche_count ?? 0 }} found
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Interactive Sentence-by-Sentence Correction Queue -->
          <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 class="text-sm font-bold uppercase tracking-wider text-slate-200">
                  Sentence Correction Queue
                </h3>
                <p class="text-xs text-slate-400">
                  Review flagged AI sentences &amp; accept or customize rewrites
                </p>
              </div>

              <button
                v-if="unfixedFlaggedCount > 0"
                @click="acceptAllTopSuggestions"
                class="px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow transition"
              >
                ✨ Accept All {{ unfixedFlaggedCount }} Fixes
              </button>
            </div>

            <!-- Queue List -->
            <div v-if="flaggedSentences.length > 0" class="space-y-3 max-h-[500px] overflow-y-auto pr-1">
              <div
                v-for="sent in flaggedSentences"
                :key="sent.id"
                @click="selectSentence(sent.id)"
                class="p-3.5 rounded-xl border transition cursor-pointer space-y-2.5"
                :class="
                  selectedSentenceId === sent.id
                    ? 'bg-slate-950 border-indigo-500 shadow-md'
                    : sent.accepted
                    ? 'bg-emerald-950/15 border-emerald-800/50 hover:border-emerald-700'
                    : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
                "
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="text-xs font-semibold text-slate-400">
                    Sentence #{{ sent.id + 1 }}
                  </span>
                  <span
                    class="text-[11px] font-bold px-2 py-0.5 rounded-full"
                    :class="
                      sent.accepted
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : sent.status === 'ai'
                        ? 'bg-rose-500/20 text-rose-300'
                        : 'bg-amber-500/20 text-amber-300'
                    "
                  >
                    {{ sent.accepted ? '✓ Humanized' : `${sent.ai_probability}% AI` }}
                  </span>
                </div>

                <!-- Current / Original Sentence -->
                <p class="text-xs text-slate-200 leading-relaxed">
                  {{ sent.text }}
                </p>

                <!-- Top Recommended Rewrite Quick-Action -->
                <div
                  v-if="!sent.accepted && sent.suggestions && sent.suggestions.length > 0"
                  class="p-2.5 rounded-lg bg-indigo-950/30 border border-indigo-500/30 space-y-2"
                  @click.stop
                >
                  <div class="flex items-center justify-between">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-indigo-300">
                      Suggested Fix ({{ sent.suggestions[0].label }})
                    </span>
                    <div class="flex items-center gap-1.5">
                      <button
                        @click="applyRewrite(sent, sent.suggestions[0].text)"
                        class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition"
                      >
                        ✓ Accept
                      </button>
                      <button
                        @click="selectSentence(sent.id); openManualEdit(sent)"
                        class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] transition"
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                  <p class="text-xs text-indigo-100 leading-relaxed">
                    "{{ sent.suggestions[0].text }}"
                  </p>
                </div>
              </div>
            </div>

            <div
              v-else-if="analysisResult"
              class="p-6 rounded-xl bg-emerald-950/20 border border-emerald-800/40 text-center space-y-1"
            >
              <div class="text-2xl">🎉</div>
              <div class="text-sm font-semibold text-emerald-300">
                Zero AI-Flagged Sentences Detected!
              </div>
              <p class="text-xs text-slate-400">
                This document reads with natural human cadence and authentic phrasing.
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- LLM API Key / Provider Settings Modal -->
    <div
      v-if="showSettingsModal"
      class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      @click.self="showSettingsModal = false"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-base font-bold text-white">External LLM API Configuration</h3>
          <button @click="showSettingsModal = false" class="text-slate-400 hover:text-white text-sm">✕</button>
        </div>

        <p class="text-xs text-slate-400 leading-relaxed">
          Configure an API key in your root <code class="text-indigo-300">.env</code> file or enter one below for this session.
        </p>

        <div class="space-y-3">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Provider</label>
            <select
              v-model="llmSettings.provider"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="openai">OpenAI (gpt-4o-mini)</option>
              <option value="gemini">Google Gemini (gemini-2.0-flash)</option>
              <option value="anthropic">Anthropic Claude (claude-3-5-haiku-latest)</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">
              API Key <span class="text-slate-500">(Leave blank to use backend .env key)</span>
            </label>
            <input
              v-model="llmSettings.apiKey"
              type="password"
              placeholder="sk-... or AIza..."
              class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button
            @click="showSettingsModal = false"
            class="px-4 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300"
          >
            Close
          </button>
          <button
            @click="saveSettingsAndRescan"
            class="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            Save &amp; Re-Scan
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Suggestion {
  label: string
  tone: string
  text: string
}

interface SentenceItem {
  id: number
  text: string
  original_text: string
  ai_probability: number
  initial_ai_probability?: number
  status: 'ai' | 'mixed' | 'human'
  reasons: string[]
  suggestions: Suggestion[]
  accepted: boolean
}

interface SamplePreset {
  id: string
  title: string
  badge: string
  description: string
  text: string
}

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const samples = ref<SamplePreset[]>([])
const activeSampleId = ref<string>('ai-corporate')
const inputText = ref<string>('')
const viewMode = ref<'inspector' | 'editor'>('inspector')
const isAnalyzing = ref<boolean>(false)
const analysisResult = ref<any>(null)
const sentences = ref<SentenceItem[]>([])
const selectedSentenceId = ref<number | null>(null)
const initialAiScore = ref<number>(0)

const editingSentenceId = ref<number | null>(null)
const manualEditText = ref<string>('')
const regeneratingId = ref<number | null>(null)
const copied = ref<boolean>(false)

const showSettingsModal = ref<boolean>(false)
const llmSettings = ref({
  provider: 'gemini',
  apiKey: ''
})

const wordCount = computed(() => {
  const trimmed = inputText.value.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
})

const characterCount = computed(() => inputText.value.length)

const selectedSentence = computed(() =>
  sentences.value.find((s) => s.id === selectedSentenceId.value) || null
)

const flaggedSentences = computed(() =>
  sentences.value.filter(
    (s) => s.status === 'ai' || s.status === 'mixed' || s.accepted
  )
)

const totalFlaggedCount = computed(() => flaggedSentences.value.length)
const acceptedCount = computed(
  () => flaggedSentences.value.filter((s) => s.accepted).length
)
const unfixedFlaggedCount = computed(
  () => flaggedSentences.value.filter((s) => !s.accepted).length
)

const liveAiScore = computed(() => {
  if (!sentences.value.length) return 0
  const sum = sentences.value.reduce((acc, s) => acc + s.ai_probability, 0)
  return Math.round(sum / sentences.value.length)
})

const scoreReduction = computed(() =>
  Math.max(0, initialAiScore.value - liveAiScore.value)
)

const liveVerdict = computed(() => {
  if (liveAiScore.value >= 65) return 'Likely AI-Generated'
  if (liveAiScore.value >= 40) return 'Mixed AI & Human'
  return 'Authentic Human Writing'
})

const isLiveLlm = computed(() => Boolean(analysisResult.value?.is_live_llm))
const activeProviderLabel = computed(() => {
  const prov = analysisResult.value?.provider_used || 'ready'
  if (prov === 'heuristic_fallback') return 'Built-in Forensic NLP (Add API Key for LLM)'
  return `${prov} (${analysisResult.value?.model_used || ''})`
})

function getSentenceHighlightClass(sent: SentenceItem) {
  const isSelected = selectedSentenceId.value === sent.id
  const ring = isSelected ? 'ring-2 ring-indigo-400 ' : ''
  if (sent.accepted) {
    return ring + 'bg-emerald-500/20 text-emerald-100 border-b-2 border-emerald-400'
  }
  if (sent.status === 'ai') {
    return ring + 'bg-rose-500/25 hover:bg-rose-500/35 text-rose-100 border-b-2 border-rose-500'
  }
  if (sent.status === 'mixed') {
    return ring + 'bg-amber-500/25 hover:bg-amber-500/35 text-amber-100 border-b-2 border-amber-500'
  }
  return ring + 'hover:bg-slate-800/80 text-slate-200'
}

function selectSentence(id: number) {
  selectedSentenceId.value = id
  editingSentenceId.value = null
}

function syncInputTextFromSentences() {
  inputText.value = sentences.value.map((s) => s.text).join(' ')
}

function applyRewrite(sent: SentenceItem, newText: string) {
  if (!newText.trim()) return
  if (sent.initial_ai_probability === undefined) {
    sent.initial_ai_probability = sent.ai_probability
  }
  sent.text = newText.trim()
  sent.ai_probability = 8
  sent.accepted = true
  editingSentenceId.value = null
  syncInputTextFromSentences()
}

function revertSentence(sent: SentenceItem) {
  sent.text = sent.original_text
  sent.ai_probability = sent.initial_ai_probability ?? 85
  sent.accepted = false
  syncInputTextFromSentences()
}

function dismissSentenceFlag(sent: SentenceItem) {
  if (sent.initial_ai_probability === undefined) {
    sent.initial_ai_probability = sent.ai_probability
  }
  sent.ai_probability = 15
  sent.accepted = true
}

function openManualEdit(sent: SentenceItem) {
  editingSentenceId.value = sent.id
  manualEditText.value = sent.text
}

function acceptAllTopSuggestions() {
  for (const sent of sentences.value) {
    if ((sent.status === 'ai' || sent.status === 'mixed') && !sent.accepted) {
      if (sent.suggestions && sent.suggestions.length > 0) {
        applyRewrite(sent, sent.suggestions[0].text)
      }
    }
  }
}

async function regenerateSentenceSuggestions(sent: SentenceItem) {
  regeneratingId.value = sent.id
  try {
    const res: any = await $fetch(`${apiBase}/api/correct-sentence`, {
      method: 'POST',
      body: {
        sentence: sent.original_text,
        context_text: inputText.value,
        tone: 'natural',
        provider: llmSettings.value.apiKey ? llmSettings.value.provider : undefined,
        api_key: llmSettings.value.apiKey || undefined
      }
    })
    if (res?.suggestions?.length) {
      sent.suggestions = res.suggestions
    }
  } catch (err) {
    console.error('Failed to regenerate suggestions:', err)
  } finally {
    regeneratingId.value = null
  }
}

async function runAnalysis() {
  if (!inputText.value.trim()) return
  isAnalyzing.value = true
  try {
    const res: any = await $fetch(`${apiBase}/api/analyze`, {
      method: 'POST',
      body: {
        text: inputText.value,
        provider: llmSettings.value.apiKey ? llmSettings.value.provider : undefined,
        api_key: llmSettings.value.apiKey || undefined
      }
    })
    analysisResult.value = res
    sentences.value = (res.sentences || []).map((s: SentenceItem) => ({
      ...s,
      initial_ai_probability: s.ai_probability
    }))
    initialAiScore.value = liveAiScore.value
    viewMode.value = 'inspector'

    const firstFlagged = sentences.value.find(
      (s) => s.status === 'ai' || s.status === 'mixed'
    )
    selectedSentenceId.value = firstFlagged
      ? firstFlagged.id
      : sentences.value[0]?.id ?? null
  } catch (err) {
    console.error('Analysis failed:', err)
  } finally {
    isAnalyzing.value = false
  }
}

async function loadSample(sample: SamplePreset) {
  activeSampleId.value = sample.id
  inputText.value = sample.text
  await runAnalysis()
}

function saveSettingsAndRescan() {
  showSettingsModal.value = false
  runAnalysis()
}

async function copyCurrentText() {
  try {
    await navigator.clipboard.writeText(inputText.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  try {
    const res: any = await $fetch(`${apiBase}/api/samples`)
    samples.value = res.samples || []
    if (samples.value.length > 0) {
      await loadSample(samples.value[0])
    }
  } catch (e) {
    console.error('Could not fetch samples:', e)
  }
})
</script>
