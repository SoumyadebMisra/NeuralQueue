/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "#020617",
                surface: "#0f172a",
                accent: "#38bdf8",
            },
        },
    },
    plugins: [],
}