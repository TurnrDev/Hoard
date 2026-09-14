import "@mdi/font/css/materialdesignicons.css";
import "bootstrap/dist/css/bootstrap.min.css";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./style.css";
import {
  applyThemePreferences,
  HoardLara,
  HoardLaraColourblind,
  readThemePreferences,
} from "./theme";

const themePreferences = readThemePreferences();

applyThemePreferences(themePreferences);

const app = createApp(App);

app.use(PrimeVue, {
  theme: {
    preset:
      themePreferences.palette === "colourblind" ? HoardLaraColourblind : HoardLara,
    options: {
      darkModeSelector: ".hoard-dark",
    },
  },
});

app.use(ToastService);
app.use(router).mount("#app");
