import { render, screen } from "@testing-library/react";
import { ConversationsPage } from "../pages/hr/ConversationsPage";
import { useWorkspaceStore } from "../stores/workspace-store";

describe("ConversationsPage", () => {
  it("prioritizes the candidate name over the job context", () => {
    useWorkspaceStore.setState({
      initialized: true,
      loading: false,
      error: null,
      conversations: [
        {
          id: "conversation-001",
          applicationId: "application-001",
          jobTitle: "AI 产品前端工程师",
          candidateName: "Alex Chen",
          messages: [],
        },
      ],
    });

    render(<ConversationsPage />);

    const conversationItem = screen.getByRole("button", {
      name: "Alex Chen AI 产品前端工程师",
    });
    expect(conversationItem.textContent).toBe("Alex ChenAI 产品前端工程师");
    expect(screen.getByRole("heading", { name: "Alex Chen" })).toBeInTheDocument();
    expect(screen.queryByText("与求职 Agent 沟通")).not.toBeInTheDocument();
    expect(screen.queryByText("Agent 沟通")).not.toBeInTheDocument();
  });
});
