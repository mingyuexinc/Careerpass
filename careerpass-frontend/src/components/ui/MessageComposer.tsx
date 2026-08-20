import { useState, type FormEvent } from "react";
import { Button } from "./Button";

export function MessageComposer({
  disabled,
  onSend,
}: {
  disabled?: boolean;
  onSend: (content: string, clientMessageId: string) => Promise<void>;
}) {
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const [clientMessageId, setClientMessageId] = useState<string | null>(null);
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending || disabled || !value.trim()) return;
    setSending(true);
    const requestId = clientMessageId ?? crypto.randomUUID();
    setClientMessageId(requestId);
    try {
      await onSend(value, requestId);
      setValue("");
      setClientMessageId(null);
    } finally {
      setSending(false);
    }
  }
  return (
    <form className="message-composer" onSubmit={handleSubmit}>
      <label className="visually-hidden" htmlFor="message-input">
        消息内容
      </label>
      <textarea
        id="message-input"
        value={value}
        disabled={disabled || sending}
        onChange={(event) => setValue(event.target.value)}
        placeholder="输入要发送给求职 Agent 的消息"
        rows={3}
      />
      <Button type="submit" disabled={disabled || sending || !value.trim()}>
        {sending ? "发送中…" : "发送消息"}
      </Button>
    </form>
  );
}
