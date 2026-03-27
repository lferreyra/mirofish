import './style.css'
import '@fontsource/geist-sans/400.css'
import '@fontsource/geist-sans/600.css'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(router)

app.mount('#app')
