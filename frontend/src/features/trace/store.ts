import { create } from "zustand";

import type { TraceEvent } from "@/shared/api/types";

interface TraceState {
  events: TraceEvent[];
  requestId: string | null;
  setRequestId: (requestId: string | null) => void;
  pushEvent: (event: TraceEvent) => void;
  reset: () => void;
}

export const useTraceStore = create<TraceState>((set) => ({
  events: [],
  requestId: null,
  setRequestId: (requestId) => set({ requestId, events: [] }),
  pushEvent: (event) => set((state) => ({ events: [...state.events, event] })),
  reset: () => set({ events: [], requestId: null }),
}));
