import pluginVue from 'eslint-plugin-vue'

export default [
    ...pluginVue.configs['flat/recommended'],
    {
        files: ["src/**/*.js", "src/**/*.vue"],
        ignores: [
            "source/website/src/dist/*.js",
            "source/website/src/dist/min/*.js"
        ],
        rules: {
            "no-console": "off",
            "no-undef": "off",
            "vue/require-prop-types": "off",
            "vue/attribute-hyphenation": "off",
            "vue/valid-v-for": "off",
            "vue/max-attributes-per-line": "off",
            "vue/html-self-closing": "off",
            "vue/require-explicit-emits": "off",
            "vue/multi-word-component-names": ["error", {
                ignores: [
                    "Celebrities",
                    "Entities",
                    "Loading",
                    "Subtitles",
                    "Transcript",
                    "Translation",
                    "Waveform",
                    "Home",
                    "Login",
                ]
            }],
            "vue/require-valid-default-prop": "off",
            "vue/no-deprecated-dollar-listeners-api": "off"
        }
  }
]
