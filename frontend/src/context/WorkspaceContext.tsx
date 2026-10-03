import { useEffect, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { setVocabWorkspace } from "../lib/vocab";
import { WorkspaceContext, isWorkspace, type WorkspaceId } from "./workspace";

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [params, setParams] = useSearchParams();
  const fromUrl = params.get("ws");
  const stored = localStorage.getItem("blackbox-workspace");
  const workspace: WorkspaceId = isWorkspace(fromUrl)
    ? fromUrl
    : isWorkspace(stored)
      ? stored
      : "nimbu";
  setVocabWorkspace(workspace);

  useEffect(() => {
    localStorage.setItem("blackbox-workspace", workspace);
    if (!isWorkspace(fromUrl)) {
      const next = new URLSearchParams(params);
      next.set("ws", workspace);
      setParams(next, { replace: true });
    }
  }, [fromUrl, params, setParams, workspace]);

  const setWorkspace = (nextWorkspace: WorkspaceId) => {
    localStorage.setItem("blackbox-workspace", nextWorkspace);
    const next = new URLSearchParams(params);
    next.set("ws", nextWorkspace);
    setParams(next);
  };

  return (
    <WorkspaceContext.Provider value={{ workspace, setWorkspace }}>
      {children}
    </WorkspaceContext.Provider>
  );
}