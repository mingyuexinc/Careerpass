import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageList } from "../components/ui/MessageList";

const attachment = {
  id: "attachment-001",
  fileName: "学籍验证报告.pdf",
  fileType: "pdf",
  fileSizeBytes: 2048,
  createdAt: "2026-08-21T09:00:00+08:00",
  expiresAt: "2026-08-28T09:00:00+08:00",
  status: "downloadable" as const,
};

describe("MessageList attachment delivery", () => {
  it("renders a successful attachment-only Agent message as a file card without a success prompt", () => {
    render(
      <MessageList
        agentName="Alex Chen"
        messages={[
          {
            id: "message-001",
            sender: "agent",
            text: "已为你找到相关求职资料，请点击附件下载。",
            createdAt: attachment.createdAt,
            attachments: [attachment],
          },
        ]}
      />,
    );

    expect(screen.getByRole("article", { name: "附件 学籍验证报告.pdf" })).toBeInTheDocument();
    expect(screen.getByText("学籍验证报告.pdf")).toBeInTheDocument();
    expect(screen.getByText("PDF · 2.0 KB")).toBeInTheDocument();
    expect(screen.queryByText("已为你找到相关求职资料，请点击附件下载。")).not.toBeInTheDocument();
    expect(screen.queryByText("求职 Agent")).not.toBeInTheDocument();
  });

  it("keeps download and retry states visible while preventing expired downloads", async () => {
    const user = userEvent.setup();
    const onDownload = vi.fn().mockRejectedValueOnce(new Error("附件下载失败，请稍后重试。"));
    render(
      <MessageList
        agentName="Alex Chen"
        messages={[
          {
            id: "message-001",
            sender: "agent",
            text: "",
            createdAt: attachment.createdAt,
            attachments: [
              attachment,
              { ...attachment, id: "attachment-002", fileName: "旧资料.pdf", status: "expired" },
            ],
          },
        ]}
        onDownload={onDownload}
      />,
    );

    await user.click(screen.getByRole("button", { name: "下载附件 学籍验证报告.pdf" }));
    expect(onDownload).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("附件下载失败，请稍后重试。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试下载 学籍验证报告.pdf" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "已过期 旧资料.pdf" })).toBeDisabled();
  });

  it("uses the candidate name as the Agent message subject", () => {
    render(
      <MessageList
        agentName="Alex Chen"
        messages={[
          {
            id: "message-002",
            sender: "agent",
            text: "您好，我会继续协助您了解这份投递。",
            createdAt: attachment.createdAt,
          },
        ]}
      />,
    );

    expect(screen.getByText("Alex Chen")).toBeInTheDocument();
    expect(screen.queryByText("求职 Agent")).not.toBeInTheDocument();
  });
});
