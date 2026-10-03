import { useMutation, useQuery } from "@tanstack/react-query";
import { ApiError, apiGet, apiPost } from "./client";
import type * as T from "./types";
export const useRuns = (query = "") => useQuery({ queryKey: ["runs", query], queryFn: () => apiGet<T.RunListResponse>(`/runs?${query}`) });
export const useRun = (id?: string) => useQuery({
	queryKey: ["run", id],
	queryFn: () => apiGet<T.RunDetailResponse>(`/runs/${id}`),
	enabled: Boolean(id),
	retry: (failureCount, error) =>
		error instanceof ApiError && error.status === 404 && failureCount < 8,
	retryDelay: 500,
});
export const useDiagnosis = (id?: string, enabled = true) => useQuery({ queryKey: ["diagnosis", id], queryFn: () => apiGet<T.DiagnosisResponse>(`/runs/${id}/diagnosis`), enabled: Boolean(id) && enabled });
export const useReplay = (id: string) => useMutation({ mutationFn: (body: T.ReplayRequest) => apiPost<T.ReplayResponse>(`/runs/${id}/replay`, body) });
export const useBlastRadius = (id: string, key?: string) => useQuery({ queryKey: ["blast", id, key], queryFn: () => apiGet<T.BlastRadiusResponse>(`/runs/${id}/blast-radius?step_key=${encodeURIComponent(key!)}`), enabled: Boolean(id && key) });
export const useRepairJob = () => useMutation({ mutationFn: ({ id, top_k = 3 }: { id: string; top_k?: number }) => apiPost<T.JobCreatedResponse>(`/runs/${id}/repair/jobs`, { top_k }) });
export const useJob = (id?: string) => useQuery({
	queryKey: ["job", id],
	queryFn: () => apiGet<T.JobResponse>(`/jobs/${id}`),
	enabled: Boolean(id),
	refetchInterval: (query) =>
		["completed", "failed"].includes(query.state.data?.status ?? "")
			? false
			: 700,
});
export const useCompare = (a: string, b: string) => useQuery({ queryKey: ["compare", a, b], queryFn: () => apiGet<T.CompareResponse>(`/compare?a=${a}&b=${b}`), enabled: Boolean(a && b) });
export const useEval = () => useQuery({ queryKey: ["eval"], queryFn: () => apiGet<T.EvalResponse>("/eval") });
export const useFleet = () => useQuery({ queryKey: ["fleet"], queryFn: () => apiGet<T.FleetResponse>("/fleet?split=test") });
export const useTasks = (q = "") => useQuery({ queryKey: ["tasks", q], queryFn: () => apiGet<T.TaskRecord[]>(`/tasks?split=test&q=${encodeURIComponent(q)}`) });
export const useFaultTargets = (id?: string) => useQuery({ queryKey: ["targets", id], queryFn: () => apiGet<T.FaultTargetsResponse>(`/tasks/${id}/fault-targets`), enabled: Boolean(id) });
export const useLiveRun = () => useMutation({ mutationFn: (body: T.LiveRunRequest) => apiPost<T.LiveRunResponse>("/live/run", body) });
export const useHealth = () => useQuery({ queryKey: ["health"], queryFn: () => apiGet<T.HealthResponse>("/health") });