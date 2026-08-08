import type { Message } from "../../domain/types";

export function MessageList({ messages }: { messages: Message[] }) {
  return (
    <div className="message-list">
      {messages.map((message) => (
        <div
          className={`message-row ${message.sender === "hr" ? "is-hr" : "is-agent"}`}
          key={message.id}
        >
          <div className="message-bubble">
            <strong>{message.sender === "hr" ? "HR" : "求职 Agent"}</strong>
            <span>{message.text}</span>
            <time>
              {new Date(message.createdAt).toLocaleTimeString("zh-CN", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </time>
          </div>
        </div>
      ))}
    </div>
  );
}
