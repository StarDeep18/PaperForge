import { useWorkspaceSettings } from "./useWorkspaceSettings";

export type Theme = "light" | "dark";

export function useTheme() {
  const { settings, updateSettings } = useWorkspaceSettings();

  const toggleTheme = () => {
    const nextTheme = settings.theme === "light" ? "dark" : "light";
    updateSettings({ theme: nextTheme });
  };

  return {
    theme: (settings.theme as Theme) || "dark",
    toggleTheme,
  };
}
