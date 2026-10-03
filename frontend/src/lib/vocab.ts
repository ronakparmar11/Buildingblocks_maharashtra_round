import type { WorkspaceId } from "../context/workspace";

export type VocabKey =
  | "run"
  | "runs"
  | "question"
  | "finalAnswer"
  | "goldAnswer"
  | "passage"
  | "task";

let activeWorkspace: WorkspaceId = "nimbu";

const generic: Record<VocabKey, string> = {
  run: "run",
  runs: "runs",
  question: "question",
  finalAnswer: "final answer",
  goldAnswer: "expected answer",
  passage: "passage",
  task: "task",
};

const nimbu: Record<VocabKey, string> = {
  run: "conversation",
  runs: "conversations",
  question: "customer message",
  finalAnswer: "agent reply",
  goldAnswer: "correct answer (per policy)",
  passage: "help article",
  task: "support question",
};

export const setVocabWorkspace = (workspace: WorkspaceId) => {
  activeWorkspace = workspace;
};

export const t = (key: VocabKey) =>
  (activeWorkspace === "nimbu" ? nimbu : generic)[key];