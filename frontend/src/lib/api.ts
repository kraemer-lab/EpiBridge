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

export interface AnalysisBundle {
  id: string;
  project_id: string;
  created_by_id: string;
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
}

export interface AnalysisBundleCreate {
  name: string;
  runtime: string;
  version: string;
  entrypoint: string;
  description?: string;
  resource_identifiers?: string[];
  outputs?: string[];
  parameters?: Record<string, unknown>;
  status?: string;
}

export interface AnalysisBundleUpdate {
  name?: string;
  runtime?: string;
  version?: string;
  entrypoint?: string;
  description?: string;
  resource_identifiers?: string[];
  outputs?: string[];
  parameters?: Record<string, unknown>;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
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

export async function getProjectBundle(
  projectId: string,
  bundleId: string,
): Promise<AnalysisBundle> {
  return request<AnalysisBundle>(`/api/projects/${projectId}/bundles/${bundleId}`);
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

export interface DashboardStats {
  projects: number;
  jobs: number;
  outputs: number;
  resources: number;
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
