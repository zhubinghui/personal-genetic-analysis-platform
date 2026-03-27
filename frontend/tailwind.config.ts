import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0fdf4",
          100: "#dcfce7",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          900: "#14532d",
        },
        aging: {
          good: "#22c55e",      // pace < 0.9
          normal: "#eab308",    // pace 0.9-1.1
          warning: "#f97316",   // pace 1.1-1.3
          danger: "#ef4444",    // pace > 1.3
        },
      },
    },
  },
  plugins: [],
};

export default config;
