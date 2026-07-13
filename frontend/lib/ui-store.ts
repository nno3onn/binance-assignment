import { create } from "zustand";

type UiState = {
  isNavigationCollapsed: boolean;
  setNavigationCollapsed: (isNavigationCollapsed: boolean) => void;
};

export const useUiStore = create<UiState>((set) => ({
  isNavigationCollapsed: false,
  setNavigationCollapsed: (isNavigationCollapsed) =>
    set({ isNavigationCollapsed })
}));
