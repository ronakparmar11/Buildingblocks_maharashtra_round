import { mockRequest } from "../mocks/handlers";
export class ApiError extends Error { constructor(public status: number, message: string) { super(message); } }
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (import.meta.env.VITE_USE_MOCKS === "true") return mockRequest<T>(method, `/api${path}`, body);
  const response = await fetch(`/api${path}`, { method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) throw new ApiError(response.status, await response.text());
  return response.json() as Promise<T>;
}
export const apiGet = <T>(path: string) => request<T>("GET", path);
export const apiPost = <T>(path: string, body?: unknown) => request<T>("POST", path, body);
export const apiPatch = <T>(path: string, body: unknown) => request<T>("PATCH", path, body);
export const apiPut = <T>(path: string, body: unknown) => request<T>("PUT", path, body);
export const apiDelete = (path: string) => request<void>("DELETE", path);