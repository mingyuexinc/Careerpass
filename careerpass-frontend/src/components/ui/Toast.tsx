export function Toast({ message, onClose }: { message: string; onClose?: () => void }) {
  return (
    <div className="toast" role="status">
      <span>{message}</span>
      {onClose ? (
        <button type="button" aria-label="关闭提示" onClick={onClose}>
          ×
        </button>
      ) : null}
    </div>
  );
}
