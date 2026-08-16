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
    expect(running.conversations).toHaveLength(running.applications.length);
    expect(
      running.conversations.map((conversation) => conversation.applicationId),
    ).toEqual(running.applications.map((application) => application.id));
  });

  it("keeps the resume failure state available to the data layer", async () => {
    const file = new File(["resume"], "resume.pdf", { type: "application/pdf" });
    await mockRepository.uploadResume(file);
    const failed = await mockRepository.setParseResult("failed");
    expect(failed.parseStatus).toBe("failed");
  });

  it("supports the four S05 document formats without a version field", async () => {
    const uploaded = await mockRepository.uploadDocuments([
      new File(["%PDF-1.7"], "portfolio.pdf"),
      new File(["# Portfolio"], "portfolio.md"),
      new File([new Uint8Array([0xff, 0xd8, 0xff])], "portfolio.jpg"),
      new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], "portfolio.png"),
    ]);

    expect(uploaded).toHaveLength(4);
    expect(uploaded.every((item) => item.status === "success")).toBe(true);
    expect(uploaded.map((item) => item.document?.fileType)).toEqual([
      "pdf",
      "md",
      "jpg",
      "png",
    ]);
    expect(uploaded.every((item) => item.document && !("version" in item.document))).toBe(
      true,
    );
  });

  it("returns a duplicate result for the same content even when the name changes", async () => {
    const firstUpload = await mockRepository.uploadDocuments([
      new File(["portfolio"], "portfolio.pdf"),
    ]);
    const secondUpload = await mockRepository.uploadDocuments([
      new File(["portfolio"], "portfolio.md"),
    ]);

    expect(firstUpload[0].result).toBe("created");
    expect(secondUpload[0].result).toBe("duplicate");
    expect(secondUpload[0].document?.id).toBe(firstUpload[0].document?.id);
    expect((await mockRepository.getSnapshot()).supportingDocuments).toHaveLength(1);
  });

  it("keeps successful files when a batch contains failures", async () => {
    const results = await mockRepository.uploadDocuments([
      new File(["portfolio"], "portfolio.pdf"),
      new File(["not supported"], "portfolio.docx"),
      new File([], "empty.md"),
    ]);

    expect(results.map((item) => item.status)).toEqual(["success", "failed", "failed"]);
    expect(results.slice(1).map((item) => item.failureCode)).toEqual([
      "unsupported_file",
      "empty_file",
    ]);
    expect((await mockRepository.getSnapshot()).supportingDocuments).toHaveLength(1);
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

  it("allows a company-specific forward jump and finishes at the offer target", async () => {
    const file = new File(["resume"], "resume.pdf");
    await mockRepository.uploadResume(file);
    await mockRepository.setParseResult("succeeded");
    await mockRepository.saveGoal({ offerTarget: 1, title: "前端工程师", filters: "" });
    await mockRepository.startAgent();
    await mockRepository.updateApplicationStatus("application-001", "interview_1");
    expect((await mockRepository.getSnapshot()).applications[0].status).toBe(
      "interview_1",
    );
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
