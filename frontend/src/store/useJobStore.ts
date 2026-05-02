import { create } from "zustand"

type JobUiState = {
  selectedJobId: string | null
  setSelectedJobId: (id: string | null) => void
}

export const useJobStore = create<JobUiState>((set) => ({
  selectedJobId: null,
  setSelectedJobId: (id) => set({ selectedJobId: id }),
}))
