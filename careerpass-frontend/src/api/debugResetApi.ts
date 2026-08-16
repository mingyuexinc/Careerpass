interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface DebugResetData {
  reset: boolean;
  scope: "current_account";
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export async function resetCurrentAccount(accessToken: string): Promise<DebugResetData> {
  const response = await fetch(`${apiBaseUrl}/debug/reset/current-account`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = (await response.json()) as ApiEnvelope<DebugResetData>;
  if (response.status === 409) {
    throw new Error("当前账号仍有任务处理中，请稍后再恢复初始状态。 ");
  }
  if (response.status === 403) {
    throw new Error("当前环境未开启调试数据恢复。 ");
  }
  if (!response.ok || payload.data === null || !payload.data.reset) {
    throw new Error("恢复初始状态失败，请稍后重试。 ");
  }
  return payload.data;
}
