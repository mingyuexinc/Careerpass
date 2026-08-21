import {
  listCurrentConversations,
  sendConversationMessage,
  startConversationProactiveQuery,
} from "../api/conversationApi";

const conversation = {
  id: "conversation-001",
  application_id: "application-001",
  job_title: "AI 应用开发工程师",
  candidate_name: "候选人甲",
  messages: [
    {
      id: "message-001",
      sender: "agent",
      message_type: "text",
      status: "sent",
      content: "候选人使用过 Python。",
      created_at: "2026-08-20T10:00:00Z",
    },
  ],
};

describe("S10-01 conversation API", () => {
  afterEach(() => vi.restoreAllMocks());

  it("maps the safe conversation projection", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ code: 200, msg: "success", data: { total: 1, conversations: [conversation] } }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(listCurrentConversations("hr-token")).resolves.toEqual([
      {
        id: "conversation-001",
        applicationId: "application-001",
        jobTitle: "AI 应用开发工程师",
        candidateName: "候选人甲",
        messages: [
          {
            id: "message-001",
            sender: "agent",
            text: "候选人使用过 Python。",
            createdAt: "2026-08-20T10:00:00Z",
            status: "sent",
            messageType: "text",
            attachments: [],
          },
        ],
      },
    ]);
  });

  it("sends client_message_id and refreshes the visible projection", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: 200,
            msg: "success",
            data: {
              conversation_id: "conversation-001",
              received_message: { ...conversation.messages[0], sender: "hr", content: "问题" },
              agent_turn: {
                id: "turn-001",
                scene: "resume_answer",
                turn_status: "completed",
                outcome: "message_sent",
                retryable: false,
              },
              new_messages: [],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ code: 200, msg: "success", data: { total: 1, conversations: [conversation] } }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    await sendConversationMessage(
      "application-001",
      "conversation-001",
      "问题",
      "client-message-001",
      "hr-token",
    );

    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({
        conversation_id: "conversation-001",
        client_message_id: "client-message-001",
        content: "问题",
      }),
    });
  });

  it("maps the safe attachment projection without document internals", async () => {
    const attachmentConversation = {
      ...conversation,
      messages: [
        {
          ...conversation.messages[0],
          content: "已为你找到相关求职资料，请点击附件下载。",
          attachments: [
            {
              id: "attachment-001",
              file_name: "candidate_certificate.pdf",
              file_type: "pdf",
              file_size_bytes: 2048,
              created_at: "2026-08-20T10:00:00Z",
              expires_at: "2026-08-27T10:00:00Z",
              status: "downloadable",
            },
          ],
        },
      ],
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "success",
          data: { total: 1, conversations: [attachmentConversation] },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(listCurrentConversations("hr-token")).resolves.toMatchObject([
      {
        messages: [
          {
            text: "",
            attachments: [
              {
                id: "attachment-001",
                fileName: "candidate_certificate.pdf",
                fileType: "pdf",
                fileSizeBytes: 2048,
                status: "downloadable",
              },
            ],
          },
        ],
      },
    ]);
  });

  it("starts the proactive query through an explicit side-effect endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "success",
          data: { conversation_id: "conversation-001", agent_turn: null, new_messages: [] },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await startConversationProactiveQuery("application-001", "conversation-001", "hr-token");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/applications/application-001/conversation/proactive-query",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ conversation_id: "conversation-001" }),
      }),
    );
  });
});
