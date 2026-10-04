import { createContext, useContext } from "react";

export type WorkspaceId =
  | "nimbu"
  | "aavya"
  | "bhoomi"
  | "jugnu"
  | "taara"
  | "vayu"
  | "hotpot";

export const workspaceDetails = {
  nimbu: {
    name: "Nimbu Living support",
    description: "Customer support agent and help center",
  },
  aavya: {
    name: "Aavya Skincare support",
    description: "Clean beauty and skincare",
  },
  bhoomi: {
    name: "Bhoomi Organics support",
    description: "Organic grocery marketplace",
  },
  jugnu: {
    name: "Jugnu Kids support",
    description: "Children's clothing retailer",
  },
  taara: {
    name: "Taara Jewellery support",
    description: "Contemporary jewellery brand",
  },
  vayu: {
    name: "Vayu Mobility support",
    description: "Electric scooter company",
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
  value !== null && value in workspaceDetails;

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return value;
}