import { mockRepository } from "../api/mock/mockRepository";

describe("mock repository demo lifecycle", () => {
  beforeEach(async () => {
    await mockRepository.resetDemo();
  });

  it("uploads and parses a resume, then creates and starts a goal", async () => {
    const file = new File(["resume"], "resume.pdf", { type: "application/pdf" });
    const processing = await mockRepository.uploadResume(file);
    expect(processing.parseStatus).toBe("processing");
    const succeeded = await mockRepository.simulateParseResult("succeeded");
    expect(succeeded.parseStatus).toBe("succeeded");
    await mockRepository.saveGoal({
      offerTarget: 1,
      title: "前端工程师",
      filters: "深圳",
    });
    const running = await mockRepository.startAgent();
    expect(running.agentStatus).toBe("running");
    expect(running.applications).toHaveLength(2);
  });

  it("rejects invalid application transitions and finishes at the offer target", async () => {
    const file = new File(["resume"], "resume.pdf");
    await mockRepository.uploadResume(file);
    await mockRepository.simulateParseResult("succeeded");
    await mockRepository.saveGoal({ offerTarget: 1, title: "前端工程师", filters: "" });
    await mockRepository.startAgent();
    await expect(
      mockRepository.updateApplicationStatus("application-demo-001", "interview_1"),
    ).rejects.toThrow("不能直接跳转");
    await mockRepository.updateApplicationStatus("application-demo-001", "written_test");
    await mockRepository.updateApplicationStatus("application-demo-001", "interview_1");
    await mockRepository.updateApplicationStatus("application-demo-001", "interview_2");
    await mockRepository.updateApplicationStatus("application-demo-001", "interview_3");
    await mockRepository.updateApplicationStatus("application-demo-001", "hr_interview");
    await mockRepository.updateApplicationStatus("application-demo-001", "offer");
    const snapshot = await mockRepository.getSnapshot();
    expect(snapshot.applications[0].status).toBe("offer");
    expect(snapshot.agentStatus).toBe("finished");
  });

  it("returns a controlled agent reply after HR sends a message", async () => {
    const file = new File(["resume"], "resume.pdf");
    await mockRepository.uploadResume(file);
    await mockRepository.simulateParseResult("succeeded");
    await mockRepository.saveGoal({ offerTarget: 1, title: "前端工程师", filters: "" });
    await mockRepository.startAgent();
    const conversation = await mockRepository.sendConversationMessage(
      "conversation-demo-001",
      "您好，请补充项目经验。",
    );
    expect(conversation.messages.at(-1)?.sender).toBe("agent");
  });
});
