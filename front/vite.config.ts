// Configuração do Vite, o servidor que mostra o front no navegador. Já pronta.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],                       // ensina o Vite a entender React (.tsx)
  server: {
    proxy: {
      // Tudo que o front pedir em /api/... vai para a API Python na porta 8000,
      // sem o "/api" no caminho: /api/notas → http://127.0.0.1:8000/notas
      "/api": {
        target: "http://127.0.0.1:8000",
        rewrite: (caminho) => caminho.replace(/^\/api/, ""),
      },
    },
  },
});
