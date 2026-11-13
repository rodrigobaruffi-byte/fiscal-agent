// Ponto de entrada do front. Já pronto: liga o componente App à <div id="root"> do index.html.
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";

createRoot(document.getElementById("root")!).render(<App />);
