/* eslint-env node */
const { configure } = require('quasar/wrappers')
const { version } = require('./package.json')

module.exports = configure(function (/* ctx */) {
  return {
    boot: ['axios'],
    css: ['app.scss'],
    extras: ['roboto-font', 'material-icons'],
    build: {
      env: {
        APP_VERSION: version,
      },
      target: {
        browser: ['es2019', 'edge88', 'firefox78', 'chrome87', 'safari13.1'],
        node: 'node20',
      },
      vueRouterMode: 'history',
    },
    devServer: {
      port: 9000,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    framework: {
      config: {},
      plugins: ['Notify', 'Loading', 'Dialog'],
    },
    animations: [],
    ssr: { pwa: false },
    pwa: {},
    cordova: {},
    capacitor: { hideSplashscreen: true },
    electron: {
      inspectPort: 5858,
      bundler: 'packager',
      packager: {},
      builder: {
        appId: 'gerador-horarios',
      },
    },
  }
})
