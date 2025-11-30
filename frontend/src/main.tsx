import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@radix-ui/themes/styles.css";
import "./index.css";

import { App } from "./app/App.tsx";
import {
  Theme,
  // ThemePanel
} from "@radix-ui/themes";

import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <Theme appearance='dark'>
          <App />
          {/* <ThemePanel /> */}
        </Theme>
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>
);
