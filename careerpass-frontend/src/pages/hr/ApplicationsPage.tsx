import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import {
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  ProgressTimeline,
  StatusBadge,
  Toast,
} from "../../components/ui";
import { deliveryProgressMeta, deliveryProgressOrder } from "../../domain/mappings";
import type { DeliveryProgress } from "../../domain/types";
import { useDemoRefresh } from "../../features/demo/useDemoRefresh";
import { useDemoStore } from "../../stores/demo-store";

export function ApplicationsPage() {
  useDemoRefresh();
  const state = useDemoStore((store) => store);
  const [toast, setToast] = useState<string | null>(null);
  if (!state.initialized) return <LoadingState />;
  async function update(id: string, status: DeliveryProgress) {
    try {
      await state.updateApplicationStatus(id, status);
      setToast("投递进度已更新。");
    } catch {
      /* controlled by store */
    }
  }
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="HR / APPLICATIONS"
        title="管理投递进度"
        description="按岗位查看投递记录，只推进当前候选人的单条投递状态。"
      />
      {state.error ? (
        <ErrorState description={state.error} onRetry={state.clearError} />
      ) : null}
      {!state.applications.length ? (
        <EmptyState
          title="暂无投递记录"
          description="求职者启动 Agent 后，投递记录会在这里显示。"
        />
      ) : (
        <section className="application-list">
          {state.applications.map((application) => (
            <article className="application-card" key={application.id}>
              <div className="application-top">
                <div>
                  <h2>{application.jobTitle}</h2>
                  <p>{application.company} · 候选人 Alex Chen</p>
                </div>
                <StatusBadge tone={deliveryProgressMeta[application.status].tone}>
                  {deliveryProgressMeta[application.status].label}
                </StatusBadge>
              </div>
              <ProgressTimeline current={application.status} />
              <div className="status-editor">
                <label htmlFor={`status-${application.id}`}>
                  更新当前阶段
                  <select
                    id={`status-${application.id}`}
                    value={application.status}
                    disabled={
                      state.loading || deliveryProgressMeta[application.status].terminal
                    }
                    onChange={(event) =>
                      void update(application.id, event.target.value as DeliveryProgress)
                    }
                  >
                    {[...deliveryProgressOrder, "terminated" as const].map((status) => (
                      <option key={status} value={status}>
                        {deliveryProgressMeta[status].label}
                      </option>
                    ))}
                  </select>
                </label>
                <Button
                  variant="ghost"
                  type="button"
                  disabled={
                    state.loading || deliveryProgressMeta[application.status].terminal
                  }
                  onClick={() => void update(application.id, "terminated")}
                >
                  标记流程终止
                </Button>
              </div>
            </article>
          ))}
        </section>
      )}
      {toast ? <Toast message={toast} onClose={() => setToast(null)} /> : null}
    </div>
  );
}
