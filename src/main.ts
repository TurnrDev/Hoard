import { createApp } from "vue"
import { createPinia } from "pinia"
import { createVuetify } from "vuetify"
import { aliases, mdi } from "vuetify/iconsets/mdi"
import "vuetify/styles"
import "@mdi/font/css/materialdesignicons.css"

import App from "./App.vue"
import router from "./router"
import { hoardDark } from "./theme"
import "./styles/global.scss"

const vuetify = createVuetify({
  theme: {
    defaultTheme: "hoardDark",
    themes: { hoardDark },
  },
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: { mdi },
  },
  defaults: {
    VCard: { rounded: "lg" },
    VBtn: { rounded: "lg" },
    VChip: { rounded: "md" },
    VTextField: { variant: "outlined", density: "compact", hideDetails: "auto" },
    VNumberInput: { variant: "outlined", density: "compact", hideDetails: "auto" },
    VSelect: { variant: "outlined", density: "compact", hideDetails: "auto" },
  },
})

createApp(App).use(createPinia()).use(router).use(vuetify).mount("#app")
