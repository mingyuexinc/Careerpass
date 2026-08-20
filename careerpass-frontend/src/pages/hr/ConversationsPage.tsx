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
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function ConversationsPage() {
  useWorkspaceRefresh();
  const state = useWorkspaceStore((store) => store);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  if (!state.initialized) return <LoadingState />;
  const selected = state.conversations.find(
    (conversation) => conversation.id === (selectedId ?? state.conversations[0]?.id),
  );
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="HR / CONVERSATIONS"
        title="候选人沟通"
        description="查看指定候选人在对应岗位下的会话记录，并在工作台中完成沟通。"
      />
      {state.error ? (
        <ErrorState description={state.error} onRetry={state.clearError} />
      ) : null}
      {!state.conversations.length ? (
        <EmptyState
          title="尚未发起沟通"
          description="求职流程开始后，这里会出现可沟通的会话。"
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
                <strong>{conversation.candidateName}</strong>
                <span>{conversation.jobTitle}</span>
              </button>
            ))}
          </aside>
          <div className="conversation-main">
            {selected ? (
              <>
                <div className="conversation-header">
                  <div>
                    <h2>{selected.candidateName}</h2>
                    <p>{selected.jobTitle}</p>
                  </div>
                  <StatusBadge tone="success">可沟通</StatusBadge>
                </div>
                <MessageList
                  messages={selected.messages}
                  onDownload={(message, attachment) =>
                    state.downloadAttachment(
                      selected.applicationId,
                      message.id,
                      attachment.id,
                      attachment.fileName,
                    )
                  }
                />
                <MessageComposer
                  disabled={state.loading}
                  onSend={(content, clientMessageId) =>
                    state.sendMessage(selected.id, content, clientMessageId)
                  }
                />
              </>
            ) : null}
          </div>
        </section>
      )}
    </div>
  );
}
