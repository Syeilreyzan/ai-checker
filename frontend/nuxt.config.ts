// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-09-01',
  devtools: { enabled: false },
  modules: ['@nuxtjs/tailwindcss'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'
    }
  },
  app: {
    head: {
      title: 'VeriText AI — AI Origin Checker & Interactive Humanizer',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content: 'Executive PoC: Detect AI-generated text and interactively humanize flagged sentences.'
        }
      ]
    }
  }
})
