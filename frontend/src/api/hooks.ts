import { useMutation, useQuery } from "@tanstack/react-query";
import { useWorkspace } from "../context/workspace";
import { ApiError, apiDelete, apiGet, apiPatch, apiPost, apiPut } from "./client";
import type * as T from "./types";

const scoped = (path: string, workspace: string) => {
  const [pathname, query = ""] = path.split("?");
  const params = new URLSearchParams(query);
  params.set("workspace", workspace);
  return `${pathname}?${params}`;
};

export const useRuns = (query = "") => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["runs", workspace, query], queryFn: () => apiGet<T.RunListResponse>(scoped(`/runs?${query}`, workspace)) });
};
export const useRun = (id?: string, waitForCreation = false) => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["run", workspace, id], queryFn: () => apiGet<T.RunDetailResponse>(scoped(`/runs/${id}`, workspace)), enabled: Boolean(id), retry: (failureCount, error) => error instanceof ApiError && error.status === 404 && failureCount < (waitForCreation ? 60 : 8), retryDelay: 500 });
};
export const useDiagnosis = (id?: string, enabled = true) => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["diagnosis", workspace, id], queryFn: () => apiGet<T.DiagnosisResponse>(scoped(`/runs/${id}/diagnosis`, workspace)), enabled: Boolean(id) && enabled });
};
export const useReplay = (id: string) => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: (body: T.ReplayRequest) => apiPost<T.ReplayResponse>(scoped(`/runs/${id}/replay`, workspace), body) });
};
export const useBlastRadius = (id: string, key?: string) => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["blast", workspace, id, key], queryFn: () => apiGet<T.BlastRadiusResponse>(scoped(`/runs/${id}/blast-radius?step_key=${encodeURIComponent(key!)}`, workspace)), enabled: Boolean(id && key) });
};
export const useRepairJob = () => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: ({ id, top_k = 3 }: { id: string; top_k?: number }) => apiPost<T.JobCreatedResponse>(scoped(`/runs/${id}/repair/jobs`, workspace), { top_k }) });
};
export const useJob = (id?: string) => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["job", workspace, id], queryFn: () => apiGet<T.JobResponse>(scoped(`/jobs/${id}`, workspace)), enabled: Boolean(id), refetchInterval: (query) => ["completed", "failed"].includes(query.state.data?.status ?? "") ? false : 700, refetchIntervalInBackground: true });
};
export const useCompare = (a: string, b: string) => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["compare", workspace, a, b], queryFn: () => apiGet<T.CompareResponse>(scoped(`/compare?a=${a}&b=${b}`, workspace)), enabled: Boolean(a && b) });
};
export const useEval = () => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["eval", workspace], queryFn: () => apiGet<T.EvalResponse>(scoped("/eval", workspace)) });
};
export const useFleet = () => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["fleet", workspace], queryFn: () => apiGet<T.FleetResponse>(scoped("/fleet?split=test", workspace)) });
};
export const useTasks = (q = "") => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["tasks", workspace, q], queryFn: () => apiGet<T.TaskRecord[]>(scoped(`/tasks?split=test&q=${encodeURIComponent(q)}`, workspace)) });
};
export const useFaultTargets = (id?: string) => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["targets", workspace, id], queryFn: () => apiGet<T.FaultTargetsResponse>(scoped(`/tasks/${id}/fault-targets`, workspace)), enabled: Boolean(id) });
};
export const useLiveRun = () => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: (body: T.LiveRunRequest) => apiPost<T.LiveRunResponse>(scoped("/live/run", workspace), body) });
};
export const useHealth = () => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["health", workspace], queryFn: () => apiGet<T.HealthResponse>(scoped("/health", workspace)) });
};
export const useWorkspaces = () => useQuery({ queryKey: ["workspaces"], queryFn: () => apiGet<T.WorkspaceSummary[]>("/workspaces") });
export const useOverview = () => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["overview", workspace], queryFn: () => apiGet<T.OverviewResponse>(scoped("/overview", workspace)) });
};
export const useIncidents = (query = "") => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["incidents", workspace, query], queryFn: () => apiGet<T.IncidentListResponse>(scoped(`/incidents?${query}`, workspace)) });
};
export const useIncident = (id?: string) => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["incident", workspace, id], queryFn: () => apiGet<T.IncidentDetailResponse>(scoped(`/incidents/${id}`, workspace)), enabled: Boolean(id) });
};
export const usePatchIncident = (id: string) => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: (body: T.IncidentPatchRequest) => apiPatch<T.IncidentSummary>(scoped(`/incidents/${id}`, workspace), body) });
};
export const useVerifyIncident = (id: string) => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: (body: T.VerifyFixRequest) => apiPost<T.JobCreatedResponse>(scoped(`/incidents/${id}/verify-fix`, workspace), body) });
};
export const useNotifyIncident = (id: string) => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: () => apiPost<T.NotificationIdResponse>(scoped(`/incidents/${id}/notify`, workspace)) });
};
export const useNotificationStatus = () => useQuery({ queryKey: ["notification-status"], queryFn: () => apiGet<T.NotificationStatusResponse>("/notifications/status") });
export const useTestNotification = () => useMutation({ mutationFn: (body: T.NotificationTestRequest) => apiPost<T.NotificationTestResponse>("/notifications/test", body) });
export const useRecipients = () => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["recipients", workspace], queryFn: () => apiGet<T.RecipientResponse[]>(scoped("/recipients", workspace)) });
};
export const useCreateRecipient = () => useMutation({ mutationFn: (body: T.RecipientCreate) => apiPost<T.RecipientResponse>("/recipients", body) });
export const useUpdateRecipient = () => useMutation({ mutationFn: ({ id, body }: { id: string; body: T.RecipientUpdate }) => apiPatch<T.RecipientResponse>(`/recipients/${id}`, body) });
export const useDeleteRecipient = () => useMutation({ mutationFn: (id: string) => apiDelete(`/recipients/${id}`) });
export const useRules = () => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["rules", workspace], queryFn: () => apiGet<T.RuleResponse[]>(scoped("/rules", workspace)) });
};
export const useUpdateRule = () => useMutation({ mutationFn: ({ id, body }: { id: string; body: T.RuleUpdate }) => apiPut<T.RuleResponse>(`/rules/${id}`, body) });
export const useBusinessSettings = () => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["business-settings", workspace], queryFn: () => apiGet<T.BusinessSettingsResponse>(scoped("/settings/business", workspace)) });
};
export const useUpdateBusinessSettings = () => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: (body: T.BusinessSettingsRequest) => apiPut<T.BusinessSettingsResponse>(scoped("/settings/business", workspace), body) });
};
export const useNotifications = () => {
  const { workspace } = useWorkspace();
  return useQuery({ queryKey: ["notifications", workspace], queryFn: () => apiGet<T.NotificationListResponse>(scoped("/notifications", workspace)) });
};
export const useNotificationPreview = (id?: string) => useQuery({ queryKey: ["notification-preview", id], queryFn: () => apiGet<T.NotificationPreviewResponse>(`/notifications/${id}/preview`), enabled: Boolean(id) });
export const useSendDigest = () => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: () => apiPost<T.NotificationIdResponse>(scoped("/notifications/digest", workspace)) });
};
export const useSimulate = () => {
  const { workspace } = useWorkspace();
  return useMutation({ mutationFn: (body: T.SimulateRequest) => apiPost<T.JobCreatedResponse>("/simulate", { ...body, workspace }) });
};