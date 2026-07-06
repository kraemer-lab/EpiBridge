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

export function createProject(data: ProjectCreate): Promise<Project> {
  return request<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export interface DashboardStats {
  projects: number;
  jobs: number;
  outputs: number;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const projects = await getProjects();
  return {
    projects: projects.length,
    jobs: 0,
    outputs: 0,
  };
}
