import type {
  ClaimChecklist,
  EditorialDecision,
  EditorialDecisionValue,
  PlatformReadiness,
  QAResult,
  RightsReport,
  Story,
  Storyboard,
  VideoPackage
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export function fetchStories(): Promise<Story[]> {
  return request<Story[]>("/api/stories");
}

export function refreshStories(): Promise<Story[]> {
  return request<Story[]>("/api/stories/refresh", { method: "POST" });
}

export function generatePackage(storyId: string): Promise<VideoPackage> {
  return request<VideoPackage>(`/api/stories/${storyId}/package`, { method: "POST" });
}

export function fetchQA(storyId: string): Promise<QAResult> {
  return request<QAResult>(`/api/stories/${storyId}/qa`);
}

export function fetchClaims(storyId: string): Promise<ClaimChecklist> {
  return request<ClaimChecklist>(`/api/stories/${storyId}/claims`);
}

export function fetchRights(storyId: string): Promise<RightsReport> {
  return request<RightsReport>(`/api/stories/${storyId}/rights`);
}

export function fetchPlatformReadiness(storyId: string): Promise<PlatformReadiness> {
  return request<PlatformReadiness>(`/api/stories/${storyId}/platform-readiness`);
}

export function fetchDecision(storyId: string): Promise<EditorialDecision> {
  return request<EditorialDecision>(`/api/stories/${storyId}/decision`);
}

export function recordDecision(
  storyId: string,
  decision: Exclude<EditorialDecisionValue, "pending">,
  notes: string,
  editor = "editor"
): Promise<EditorialDecision> {
  return request<EditorialDecision>(`/api/stories/${storyId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, editor, notes })
  });
}

export function fetchStoryboard(storyId: string): Promise<Storyboard> {
  return request<Storyboard>(`/api/stories/${storyId}/storyboard`);
}

export function chartPreviewUrl(storyId: string): string {
  return `${API_BASE_URL}/api/stories/${storyId}/chart.svg`;
}

export function renderPreviewUrl(storyId: string): string {
  return `${API_BASE_URL}/api/stories/${storyId}/preview.html`;
}
