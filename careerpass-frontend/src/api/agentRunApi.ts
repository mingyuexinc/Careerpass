import type { AgentRunStatus, AgentRunSummary } from "../domain/types";

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface AgentRunSummaryResponse {
  id: string;
  status: "running" | "finished";
  started_at: string;
  finished_at?: string | null;
  finish_reason?: "offer_target_reached" | "no_match" | null;
}

interface AgentRunStatusResponse {
  state: AgentRunStatus["state"];
  can_start: boolean;
  run?: AgentRunSummaryResponse;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function headers(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

function toSummary(value: AgentRunSummaryResponse): AgentRunSummary {
  return {
    id: value.id,
    status: value.status,
    startedAt: value.started_at,
    finishedAt: value.finished_at ?? null,
    finishReason: value.finish_reason ?? null,
  };
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.data === null) {
    throw new Error(payload.msg || "求职 Agent 操作失败，请稍后重试。");
  }
  return payload.data;
}

export async function getCurrentAgentRun(accessToken: string): Promise<AgentRunStatus> {
  const response = await fetch(`${apiBaseUrl}/agent_runs/current`, { headers: headers(accessToken) });
  const data = await parseResponse<AgentRunStatusResponse>(response);
  return {
    state: data.state,
    canStart: data.can_start,
    run: data.run ? toSummary(data.run) : null,
  };
}

export async function startCurrentAgentRun(accessToken: string): Promise<AgentRunSummary> {
  const response = await fetch(`${apiBaseUrl}/agent_runs/current/start`, {
    method: "POST",
    headers: { ...headers(accessToken), "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  const data = await parseResponse<{ run: AgentRunSummaryResponse }>(response);
  return toSummary(data.run);
}
