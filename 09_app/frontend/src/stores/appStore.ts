import { create } from 'zustand';

// UI-only state. Mirrors the RCM reference store, minus its seeded notifications: every number in this app comes
// from the API, so the bell is derived from /api/schedule/overdue and /api/compliance/summary in TopBar.

interface AppState {
  sidebarCollapsed: boolean;
  /** A question typed into the top-bar search, handed to the Co-Pilot page to send. */
  pendingPrompt: string | null;

  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setPendingPrompt: (prompt: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  pendingPrompt: null,

  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setPendingPrompt: (prompt) => set({ pendingPrompt: prompt }),
}));
