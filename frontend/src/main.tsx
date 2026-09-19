/**
 * Browser entrypoint. Mounts the shell inside a router.
 *
 * Kept separate from AppShell so tests can render the shell with a
 * MemoryRouter instead of the browser history.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import AppShell from "@app/App";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("#root is missing from index.html");
}

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  </StrictMode>,
);
