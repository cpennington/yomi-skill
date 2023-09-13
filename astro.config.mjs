import { defineConfig } from 'astro/config';
import svelte from "@astrojs/svelte";

import tailwind from "@astrojs/tailwind";

// https://astro.build/config
export default defineConfig({
  integrations: [svelte(), tailwind()],
  experimental: {
  },
  srcDir: './src-js',
  base: "/yomi-skill",

  redirects: {
    '/': '/yomi-skill/yomi1'
  }
});