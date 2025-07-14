/*
 * @Author: ai-business-hql ai.bussiness.hql@gmail.com
 * @Date: 2025-02-17 20:53:45
 * @LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
 * @LastEditTime: 2025-05-08 17:26:19
 * @FilePath: /comfyui_copilot/ui/tailwind.config.js
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.
// Copyright (C) 2025 ComfyUI-Copilot Authors
// Licensed under the MIT License.

/** @type {import('tailwindcss').Config} */
import typography from '@tailwindcss/typography'

export default {
  corePlugins: { 
    preflight: false 
  },
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        white: 'var(--p-panel-background)',
        gray: {
          50: 'color-mix(in srgb, var(--p-text-color) 5%, transparent)',
          100: 'color-mix(in srgb, var(--p-text-color) 10%, transparent)',
          200: 'color-mix(in srgb, var(--p-text-color) 20%, transparent)',
          300: 'color-mix(in srgb, var(--p-text-color) 30%, transparent)',
          400: 'color-mix(in srgb, var(--p-text-color) 40%, transparent)',
          500: 'color-mix(in srgb, var(--p-text-color) 50%, transparent)',
          600: 'color-mix(in srgb, var(--p-text-color) 60%, transparent)',
          700: 'color-mix(in srgb, var(--p-text-color) 70%, transparent)',
          800: 'color-mix(in srgb, var(--p-text-color) 80%, transparent)',
          900: 'color-mix(in srgb, var(--p-text-color) 90%, transparent)',
        },
      },
      animation: {
        // bounce: 'bounce 1s infinite',
      }    
    },
    typography: {
      DEFAULT: {
        css: {
          '--tw-prose-links': 'inherit',
          '--tw-prose-headings': 'inherit',
        },
      },
      neutral: {
        css: {
          '--tw-prose-links': 'inherit',
          '--tw-prose-headings': 'inherit',
        },
      }
    },
  },
  plugins: [
    typography,
  ],
}