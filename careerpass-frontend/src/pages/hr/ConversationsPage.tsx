import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  MessageComposer,
  MessageList,
  StatusBadge,
} from "../../components/ui";
import { useDemoRefresh } from "../../features/demo/useDemoRefresh";
import { useDemoStore } from "../../stores/demo-store";

export function ConversationsPage() {
  useDemoRefresh();
  const state = useDemoStore((store) => store);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  if (!state.initialized) return <LoadingState />;
  const selected = state.conversations.find(
    (conversation) => conversation.id === (selectedId ?? state.conversations[0]?.id),
  );
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="HR / CONVERSATIONS"
        title="与求职 Agent 沟通"
        description="查看指定岗位和候选人的会话记录，发送消息后会收到固定 Demo 回复。"
      />
      {state.error ? (
        <ErrorState description={state.error} onRetry={state.clearError} />
      ) : null}
      {!state.conversations.length ? (
        <EmptyState
          title="尚未发起沟通"
          description="求职者启动 Agent 后，这里会出现可沟通的会话。"
        />
      ) : (
        <section className="chat-layout">
          <aside className="conversation-list">
            <div className="panel-heading">
              <h2>会话</h2>
              <StatusBadge tone="info">{state.conversations.length}</StatusBadge>
            </div>
            {state.conversations.map((conversation) => (
              <button
                type="button"
                className={`conversation-item ${conversation.id === selected?.id ? "is-active" : ""}`}
                key={conversation.id}
                onClick={() => setSelectedId(conversation.id)}
              >
                <strong>{conversation.jobTitle}</strong>
                <span>{conversation.candidateName}</span>
              </button>
            ))}
          </aside>
          <div className="conversation-main">
            {selected ? (
              <>
                <div className="conversation-header">
                  <div>
                    <h2>{selected.jobTitle}</h2>
                    <p>{selected.candidateName} · Agent 沟通</p>
                  </div>
                  <StatusBadge tone="success">可沟通</StatusBadge>
                </div>
                <MessageList messages={selected.messages} />
                <MessageComposer
                  disabled={state.loading}
                  onSend={(content) => state.sendMessage(selected.id, content)}
                />
              </>
            ) : null}
          </div>
        </section>
      )}
    </div>
  );
}
