import { createContext, useContext } from "react";

export type WorkspaceId = "nimbu" | "hotpot";

export const workspaceDetails = {
  nimbu: {
    name: "Nimbu Living support",
    description: "Customer support agent and help center",
  },
  hotpot: {
    name: "Benchmark (HotpotQA)",
    description: "Public benchmark and training workspace",
  },
} satisfies Record<WorkspaceId, { name: string; description: string }>;

export type WorkspaceContextValue = {
  workspace: WorkspaceId;
  setWorkspace: (workspace: WorkspaceId) => void;
};

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export const isWorkspace = (value: string | null): value is WorkspaceId =>
  value === "nimbu" || value === "hotpot";

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return value;
}