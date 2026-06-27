import type { QAResult, Story, VideoPackage } from "./types";

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

export function chartPreviewUrl(storyId: string): string {
  return `${API_BASE_URL}/api/stories/${storyId}/chart.svg`;
}
