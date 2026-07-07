const API_BASE = "";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface DataResource {
  id: string;
  identifier: string;
  name: string;
  alias: string;
  description: string;
  provider_type: string;
  endpoint: Record<string, unknown>;
  version: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AIBundleReview {
  id: string;
  bundle_id: string;
  status: string;
  summary: string | null;
  assessment: string | null;
  assessment_confidence: string | null;
  reviewer_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisBundle {
  id: string;
  project_id: string;
  created_by_id: string;
  execution_environment_id: string;
  name: string;
  status: string;
  runtime: string;
  version: string;
  entrypoint: string;
  description: string;
  resource_identifiers: string[];
  outputs: string[];
  parameters: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  ai_review: AIBundleReview | null;
}

export interface AnalysisBundleCreate {
  name: string;
  runtime?: string;
  execution_environment_id: string;
  version: string;
  entrypoint: string;
  source_path?: string;
  description?: string;
  resource_identifiers?: string[];
  outputs?: string[];
  parameters?: Record<string, unknown>;
  status?: string;
}

export interface AnalysisBundleUpdate {
  name?: string;
  execution_environment_id?: string;
  version?: string;
  entrypoint?: string;
  description?: string;
  resource_identifiers?: string[];
  outputs?: string[];
  parameters?: Record<string, unknown>;
}

export interface ExecutionRequest {
  id: string;
  project_id: string;
  analysis_bundle_id: string;
  name: string;
  timeout_seconds: number;
  parameter_overrides: Record<string, unknown>;
  status: string;
  requested_by_id: string;
  analysis_name: string;
  runtime: string;
  resource_identifiers: string[];
  parameters: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ExecutionRequestCreate {
  analysis_bundle_id: string;
  name?: string;
  timeout_seconds?: number;
  parameter_overrides?: Record<string, unknown>;
}

export interface Output {
  id: string;
  execution_request_id: string;
  filename: string;
  size: number;
  status: string;
  created_at: string;
}

export interface DashboardStats {
  projects: number;
  jobs: number;
  outputs: number;
  resources: number;
}

export interface ExecutionEnvironment {
  id: string;
  identifier: string;
  name: string;
  runtime: string;
  description: string;
  status: string;
  image_reference: string;
  created_at: string;
  updated_at: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function login(email: string, password: string): Promise<User> {
  return request<User>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<void> {
  return fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  }).then(() => undefined);
}

export function getCurrentUser(): Promise<User> {
  return request<User>("/api/me");
}

export function getProjects(): Promise<Project[]> {
  return request<Project[]>("/api/projects");
}

export function getProject(id: string): Promise<Project> {
  return request<Project>(`/api/projects/${id}`);
}

export function getProjectResources(id: string): Promise<DataResource[]> {
  return request<DataResource[]>(`/api/projects/${id}/resources`);
}

export function getProjectBundles(id: string): Promise<AnalysisBundle[]> {
  return request<AnalysisBundle[]>(`/api/projects/${id}/bundles`);
}

export function createProject(data: ProjectCreate): Promise<Project> {
  return request<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getAdminResources(): Promise<DataResource[]> {
  return request<DataResource[]>("/api/admin/resources");
}

export async function getAdminResource(id: string): Promise<DataResource> {
  return request<DataResource>(`/api/admin/resources/${id}`);
}

export async function getAdminBundles(): Promise<AnalysisBundle[]> {
  return request<AnalysisBundle[]>("/api/admin/bundles");
}

export async function getAdminBundle(id: string): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(`/api/admin/bundles/${id}`);
}

export async function createProjectBundle(
  projectId: string,
  data: AnalysisBundleCreate,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(`/api/projects/${projectId}/bundles`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function uploadProjectBundle(
  projectId: string,
  formData: FormData,
): Promise<AnalysisBundle> {
  const res = await fetch(`/api/projects/${projectId}/bundles/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  if (!res.ok) {
    const detail = await res.json().then((b) => b.detail).catch(() => res.statusText);
    throw new Error(`Upload failed: ${detail}`);
  }
  return res.json();
}

export async function attachProjectResources(
  projectId: string,
  resourceIdentifiers: string[],
): Promise<DataResource[]> {
  return request<DataResource[]>(`/api/projects/${projectId}/resources`, {
    method: "POST",
    body: JSON.stringify({ resource_identifiers: resourceIdentifiers }),
  });
}

export async function detachProjectResource(
  projectId: string,
  resourceId: string,
): Promise<void> {
  await fetch(`/api/projects/${projectId}/resources/${resourceId}`, {
    method: "DELETE",
    credentials: "include",
  });
}

export async function getProjectBundle(
  projectId: string,
  bundleId: string,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(`/api/projects/${projectId}/bundles/${bundleId}`);
}

export async function triggerAiReview(
  projectId: string,
  bundleId: string,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(
    `/api/projects/${projectId}/bundles/${bundleId}/ai-review`,
    { method: "POST" },
  );
}

export async function updateProjectBundle(
  projectId: string,
  bundleId: string,
  data: AnalysisBundleUpdate,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(`/api/projects/${projectId}/bundles/${bundleId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function createExecutionRequest(
  projectId: string,
  data: ExecutionRequestCreate,
): Promise<ExecutionRequest> {
  return request<ExecutionRequest>(
    `/api/projects/${projectId}/execution-requests`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  );
}

export async function getProjectExecutionRequests(
  projectId: string,
): Promise<ExecutionRequest[]> {
  return request<ExecutionRequest[]>(
    `/api/projects/${projectId}/execution-requests`,
  );
}

export async function getProjectExecutionRequest(
  projectId: string,
  requestId: string,
): Promise<ExecutionRequest> {
  return request<ExecutionRequest>(
    `/api/projects/${projectId}/execution-requests/${requestId}`,
  );
}

export async function getExecutionRequestOutputs(
  projectId: string,
  requestId: string,
): Promise<Output[]> {
  return request<Output[]>(
    `/api/projects/${projectId}/execution-requests/${requestId}/outputs`,
  );
}

export function getOutputDownloadUrl(
  projectId: string,
  requestId: string,
  outputId: string,
): string {
  return `/api/projects/${projectId}/execution-requests/${requestId}/outputs/${outputId}/download`;
}

export async function getExecutionEnvironments(): Promise<ExecutionEnvironment[]> {
  return request<ExecutionEnvironment[]>("/api/execution-environments");
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const [projects, resources] = await Promise.all([
    getProjects(),
    getAdminResources().catch(() => [] as DataResource[]),
  ]);
  return {
    projects: projects.length,
    jobs: 0,
    outputs: 0,
    resources: resources.length,
  };
}
