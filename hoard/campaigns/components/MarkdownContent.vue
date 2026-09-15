<template>
  <div
    class="markdown-content"
    v-html="renderedMarkdown"
  />
</template>

<script lang="ts">
import DOMPurify from "dompurify";
import { marked } from "marked";
import { defineComponent } from "vue";

export default defineComponent({
  props: {
    source: {
      type: String,
      required: true,
    },
  },
  computed: {
    renderedMarkdown(): string {
      const html = marked.parse(this.source, {
        async: false,
        breaks: true,
        gfm: true,
      }) as string;

      return DOMPurify.sanitize(html);
    },
  },
});
</script>

<style scoped>
.markdown-content :deep(> :last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
}

.markdown-content :deep(pre) {
  max-width: 100%;
  overflow-x: auto;
}
</style>
