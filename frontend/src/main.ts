import { createApp } from "vue";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import "@mdi/font/css/materialdesignicons.css";
import "vuetify/styles";
import "./style.css";
import App from "./App.vue";
import router from "./router";

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: "hoardDark",
    themes: {
      hoardDark: {
        dark: true,
        colors: {
          primary: "#c89b5b",
          secondary: "#9bb9ad",
          success: "#78c7a4",
          info: "#8fc5e8",
          warning: "#f0c36d",
          error: "#ff9898",
          surface: "#1b211f",
          background: "#111513",
        },
      },
    },
  },
});

createApp(App).use(vuetify).use(router).mount("#app");
