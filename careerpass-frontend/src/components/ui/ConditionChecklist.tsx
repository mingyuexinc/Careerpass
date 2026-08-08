export function ConditionChecklist({
  items,
}: {
  items: Array<{ label: string; done: boolean }>;
}) {
  return (
    <div className="condition-list">
      {items.map((item, index) => (
        <div className={`condition-item ${item.done ? "is-done" : ""}`} key={item.label}>
          <span className="condition-marker">{item.done ? "✓" : index + 1}</span>
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
