const API_BASE = "";
export const API_TIMEOUT_MS = 30000;

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  capabilities: string[];
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
  build_strategy: string;
  build_status: string;
  build_error: string;
  build_log: string;
  runtime: string;
  display_runtime: string;
  version: string;
  entrypoint: string;
  interpreter: string;
  arguments: string;
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
  interpreter?: string;
  arguments?: string;
  source_path?: string;
  description?: string;
  resource_identifiers?: string[];
  outputs?: string[];
  parameters?: Record<string, unknown>;
  build_strategy?: string;
  status?: string;
}

export interface AnalysisBundleUpdate {
  name?: string;
  execution_environment_id?: string;
  version?: string;
  entrypoint?: string;
  interpreter?: string;
  arguments?: string;
  description?: string;
  resource_identifiers?: string[];
  outputs?: string[];
  parameters?: Record<string, unknown>;
  build_strategy?: string;
}

export interface ExecutionRequest {
  id: string;
  project_id: string;
  analysis_bundle_id: string;
  name: string;
  timeout_seconds: number;
  parameter_overrides: Record<string, unknown>;
  status: string;
  log: string;
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
  output_set_id: string;
  filename: string;
  size: number;
  created_at: string;
}

export interface OutputSet {
  id: string;
  execution_request_id: string;
  execution_request_name: string;
  status: string;
  release_package_size: number | null;
  outputs: Output[];
  file_count: number;
  created_at: string;
  updated_at: string;
}

export interface OutputSetListItem {
  id: string;
  execution_request_id: string;
  execution_request_name: string;
  status: string;
  file_count: number;
  release_package_size: number | null;
  created_at: string;
  updated_at: string;
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
  display_name: string;
  created_at: string;
  updated_at: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      signal: controller.signal,
      ...options,
    });
    if (res.status === 401
        && !path.includes("/api/auth/login")
        && typeof window !== "undefined"
        && window.location.pathname !== "/login"
    ) {
      window.location.href = "/login";
      throw new Error("Session expired");
    }
    if (!res.ok) {
      const detail = await res.json().then((b) => b.detail).catch(() => res.statusText);
      throw new Error(detail);
    }
    return res.json();
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
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

export async function getAdminOutputSets(): Promise<OutputSetListItem[]> {
  return request<OutputSetListItem[]>("/api/admin/output-sets");
}

export async function getAdminOutputSet(id: string): Promise<OutputSet> {
  return request<OutputSet>(`/api/admin/output-sets/${id}`);
}

export async function getAdminExecutionRequests(): Promise<ExecutionRequest[]> {
  return request<ExecutionRequest[]>("/api/admin/execution-requests");
}

export async function getAdminOutput(outputId: string): Promise<Output> {
  return request<Output>(`/api/admin/outputs/${outputId}`);
}

export async function approveOutputSet(outputSetId: string): Promise<OutputSet> {
  return request<OutputSet>(`/api/admin/output-sets/${outputSetId}/approve`, { method: "POST" });
}

export async function rejectOutputSet(outputSetId: string): Promise<OutputSet> {
  return request<OutputSet>(`/api/admin/output-sets/${outputSetId}/reject`, { method: "POST" });
}

export async function releaseOutputSet(outputSetId: string): Promise<OutputSet> {
  return request<OutputSet>(`/api/admin/output-sets/${outputSetId}/release`, { method: "POST" });
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

export async function submitBundle(
  projectId: string,
  bundleId: string,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(
    `/api/projects/${projectId}/bundles/${bundleId}/submit`,
    { method: "POST" },
  );
}

export async function approveBundle(
  bundleId: string,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(
    `/api/admin/bundles/${bundleId}/approve`,
    { method: "POST" },
  );
}

export async function rejectBundle(
  bundleId: string,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(
    `/api/admin/bundles/${bundleId}/reject`,
    { method: "POST" },
  );
}

export async function supersedeBundle(
  bundleId: string,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(
    `/api/admin/bundles/${bundleId}/supersede`,
    { method: "POST" },
  );
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
): Promise<OutputSet> {
  return request<OutputSet>(
    `/api/projects/${projectId}/execution-requests/${requestId}/outputs`,
  );
}

export function getOutputSetDownloadUrl(
  projectId: string,
  requestId: string,
): string {
  return `/api/projects/${projectId}/execution-requests/${requestId}/outputs/download`;
}

export interface ArtefactList {
  artefacts: string[];
}

export async function getExecutionEnvironments(): Promise<ExecutionEnvironment[]> {
  return request<ExecutionEnvironment[]>("/api/execution-environments");
}

export async function getExecutionEnvironment(identifier: string): Promise<ExecutionEnvironment> {
  return request<ExecutionEnvironment>(`/api/execution-environments/${identifier}`);
}

export async function getEnvironmentArtefacts(identifier: string): Promise<ArtefactList> {
  return request<ArtefactList>(`/api/execution-environments/${identifier}/artefacts`);
}

export function getEnvironmentArtefactUrl(identifier: string, path: string): string {
  return `/api/execution-environments/${identifier}/artefacts/${path}`;
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

// --- Audit Events ---

export interface AuditEvent {
  id: string;
  event_type: string;
  actor_id: string;
  actor_display_name: string;
  actor_email: string;
  project_id: string | null;
  resource_type: string;
  resource_id: string;
  event_metadata: Record<string, unknown>;
  occurred_at: string;
}

export interface AuditEventList {
  items: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
}

export function getAuditEvents(params?: {
  project_id?: string;
  actor_id?: string;
  resource_type?: string;
  resource_id?: string;
  event_type?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
  order?: "asc" | "desc";
}): Promise<AuditEventList> {
  const searchParams = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    }
  }
  const qs = searchParams.toString();
  return request<AuditEventList>(`/api/admin/audit-events${qs ? `?${qs}` : ""}`);
}

// --- Identity Management ---

export interface UserCreate {
  email: string;
  display_name: string;
  password: string;
  role: string;
}

export interface ProjectMember {
  user_id: string;
  email: string;
  display_name: string;
  added_at: string;
}

export async function getUsers(): Promise<User[]> {
  return request<User[]>("/api/admin/users");
}

export async function getUser(id: string): Promise<User> {
  return request<User>(`/api/admin/users/${id}`);
}

export async function createUser(data: UserCreate): Promise<User> {
  return request<User>("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getProjectMembers(projectId: string): Promise<ProjectMember[]> {
  return request<ProjectMember[]>(`/api/projects/${projectId}/members`);
}

export async function addProjectMember(projectId: string, email: string): Promise<ProjectMember> {
  return request<ProjectMember>(`/api/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function removeProjectMember(projectId: string, userId: string): Promise<void> {
  await fetch(`/api/projects/${projectId}/members/${userId}`, {
    method: "DELETE",
    credentials: "include",
  });
}
