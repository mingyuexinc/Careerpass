import { mockRepository } from "../api/mock/mockRepository";

describe("mock repository workspace lifecycle", () => {
  beforeEach(async () => {
    await mockRepository.resetData();
  });

  it("uploads and parses a resume, then creates and starts a goal", async () => {
    const file = new File(["resume"], "resume.pdf", { type: "application/pdf" });
    const processing = await mockRepository.uploadResume(file);
    expect(processing.parseStatus).toBe("processing");
    const succeeded = await mockRepository.setParseResult("succeeded");
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

  it("keeps the resume failure state available to the data layer", async () => {
    const file = new File(["resume"], "resume.pdf", { type: "application/pdf" });
    await mockRepository.uploadResume(file);
    const failed = await mockRepository.setParseResult("failed");
    expect(failed.parseStatus).toBe("failed");
  });

  it("increments supporting document versions for the same file name", async () => {
    const file = new File(["portfolio"], "portfolio.pdf", { type: "application/pdf" });
    const firstUpload = await mockRepository.uploadDocuments([file]);
    const secondUpload = await mockRepository.uploadDocuments([file]);
    expect(firstUpload[0].version).toBe(1);
    expect(secondUpload[0].version).toBe(2);
  });

  it("deletes a supporting document from the repository", async () => {
    const uploaded = await mockRepository.uploadDocuments([
      new File(["certificate"], "certificate.pdf"),
      new File(["portfolio"], "portfolio.pdf"),
    ]);
    const remaining = await mockRepository.deleteDocument(uploaded[0].id);
    expect(remaining).toHaveLength(1);
    expect(remaining[0].fileName).toBe("portfolio.pdf");
  });

  it("keeps job file metadata and increments its replacement version", async () => {
    const firstFile = new File(["job"], "frontend-job.pdf", {
      type: "application/pdf",
    });
    const replacementFile = new File(["job"], "frontend-job-v2.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    const firstUpload = await mockRepository.uploadJob(firstFile);
    const secondUpload = await mockRepository.uploadJob(replacementFile);
    expect(firstUpload).toMatchObject({ fileName: "frontend-job.pdf", version: 1 });
    expect(secondUpload).toMatchObject({
      fileName: "frontend-job-v2.docx",
      version: 2,
    });
    expect(secondUpload.uploadedAt).toBeTruthy();
  });

  it("keeps multiple uploaded jobs for the bounded result list", async () => {
    const files = [1, 2, 3, 4, 5].map(
      (index) => new File([`job-${index}`], `job-${index}.pdf`),
    );
    for (const file of files) await mockRepository.uploadJob(file);
    const snapshot = await mockRepository.getSnapshot();
    expect(snapshot.jobs).toHaveLength(5);
    expect(new Set(snapshot.jobs.map((job) => job.id)).size).toBe(5);
    expect(snapshot.currentJob?.fileName).toBe("job-5.pdf");
  });

  it("deletes exactly the selected job after more than four jobs are uploaded", async () => {
    const files = [1, 2, 3, 4, 5].map(
      (index) => new File([`job-${index}`], `job-${index}.pdf`),
    );
    const uploaded = await mockRepository.uploadJobs(files);
    const removedIds = [uploaded[0].id, uploaded[2].id];

    const afterFirstDelete = await mockRepository.deleteJob(removedIds[0]);
    expect(afterFirstDelete).toHaveLength(4);
    expect(afterFirstDelete.some((job) => job.id === removedIds[0])).toBe(false);

    const afterSecondDelete = await mockRepository.deleteJob(removedIds[1]);
    expect(afterSecondDelete).toHaveLength(3);
    expect(afterSecondDelete.some((job) => job.id === removedIds[1])).toBe(false);
    expect(new Set(afterSecondDelete.map((job) => job.id)).size).toBe(3);
  });

  it("uploads multiple job files in one repository action", async () => {
    const files = [
      new File(["job-1"], "job-1.pdf"),
      new File(["job-2"], "job-2.docx"),
      new File(["job-3"], "job-3.pdf"),
    ];
    const uploaded = await mockRepository.uploadJobs(files);
    expect(uploaded).toHaveLength(3);
    expect((await mockRepository.getSnapshot()).jobs).toHaveLength(3);
    expect((await mockRepository.getSnapshot()).currentJob?.fileName).toBe("job-3.pdf");
  });

  it("deletes a job and restores the previous job as current", async () => {
    const uploaded = await mockRepository.uploadJobs([
      new File(["job-1"], "job-1.pdf"),
      new File(["job-2"], "job-2.pdf"),
    ]);
    const remaining = await mockRepository.deleteJob(uploaded[1].id);
    expect(remaining).toHaveLength(1);
    expect((await mockRepository.getSnapshot()).currentJob?.id).toBe(uploaded[0].id);
  });

  it("rejects invalid application transitions and finishes at the offer target", async () => {
    const file = new File(["resume"], "resume.pdf");
    await mockRepository.uploadResume(file);
    await mockRepository.setParseResult("succeeded");
    await mockRepository.saveGoal({ offerTarget: 1, title: "前端工程师", filters: "" });
    await mockRepository.startAgent();
    await expect(
      mockRepository.updateApplicationStatus("application-001", "interview_1"),
    ).rejects.toThrow("不能直接跳转");
    await mockRepository.updateApplicationStatus("application-001", "written_test");
    await mockRepository.updateApplicationStatus("application-001", "interview_1");
    await mockRepository.updateApplicationStatus("application-001", "interview_2");
    await mockRepository.updateApplicationStatus("application-001", "interview_3");
    await mockRepository.updateApplicationStatus("application-001", "hr_interview");
    await mockRepository.updateApplicationStatus("application-001", "offer");
    const snapshot = await mockRepository.getSnapshot();
    expect(snapshot.applications[0].status).toBe("offer");
    expect(snapshot.agentStatus).toBe("finished");
  });

  it("returns a controlled agent reply after HR sends a message", async () => {
    const file = new File(["resume"], "resume.pdf");
    await mockRepository.uploadResume(file);
    await mockRepository.setParseResult("succeeded");
    await mockRepository.saveGoal({ offerTarget: 1, title: "前端工程师", filters: "" });
    await mockRepository.startAgent();
    const conversation = await mockRepository.sendConversationMessage(
      "conversation-001",
      "您好，请补充项目经验。",
    );
    expect(conversation.messages.at(-1)?.sender).toBe("agent");
  });
});
