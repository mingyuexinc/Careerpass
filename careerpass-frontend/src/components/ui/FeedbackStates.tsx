interface FeedbackProps {
  title?: string;
  description?: string;
}

export function LoadingState({
  title = "正在加载",
  description = "请稍候，页面正在加载数据。",
}: FeedbackProps) {
  return (
    <div className="feedback-card" role="status">
      <span className="spinner" />
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
    </div>
  );
}

export function EmptyState({
  title = "暂无数据",
  description = "完成前置操作后，这里会显示相关内容。",
}: FeedbackProps) {
  return (
    <div className="feedback-card empty-state">
      <span className="empty-icon">○</span>
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
    </div>
  );
}

export function ErrorState({
  title = "暂时无法完成操作",
  description = "请稍后重试。",
  onRetry,
}: FeedbackProps & { onRetry?: () => void }) {
  return (
    <div className="feedback-card error-state">
      <span className="empty-icon">!</span>
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
        {onRetry ? (
          <button className="button button-secondary" type="button" onClick={onRetry}>
            重新尝试
          </button>
        ) : null}
      </div>
    </div>
  );
}
