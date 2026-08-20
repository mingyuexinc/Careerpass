import type {
  Application,
  HrApplication,
  AgentRunSummary,
  Conversation,
  WorkspaceSnapshot,
  DeliveryProgress,
  Job,
  JobGoal,
  JobGoalInput,
  Resume,
  SupportingDocument,
  SupportingDocumentUploadResult,
} from "../../domain/types";

export interface ResumeRepository {
  getCurrentResume(): Promise<Resume | null>;
  uploadResume(file: File): Promise<Resume>;
  setParseResult(result: "succeeded" | "failed"): Promise<Resume>;
}

export interface SupportingDocumentRepository {
  listDocuments(): Promise<SupportingDocument[]>;
  uploadDocuments(files: File[]): Promise<SupportingDocumentUploadResult[]>;
}

export interface JobRepository {
  listJobs(): Promise<Job[]>;
  getCurrentJob(): Promise<Job | null>;
  uploadJobs(files: File[]): Promise<Job[]>;
  uploadJob(file: File): Promise<Job>;
  deleteJob(id: string): Promise<Job[]>;
}

export interface JobGoalRepository {
  getCurrentGoal(): Promise<JobGoal | null>;
  saveGoal(input: JobGoalInput): Promise<JobGoal>;
  startAgent(): Promise<AgentRunSummary>;
}

export interface ApplicationRepository {
  listApplications(): Promise<Application[]>;
  updateApplicationStatus(id: string, status: DeliveryProgress): Promise<Application>;
  listHrApplications(): Promise<HrApplication[]>;
  updateHrApplicationStatus(id: string, status: DeliveryProgress): Promise<HrApplication>;
}

export interface ConversationRepository {
  listConversations(): Promise<Conversation[]>;
  sendConversationMessage(id: string, content: string, clientMessageId?: string): Promise<Conversation>;
  downloadConversationAttachment(applicationId: string, messageId: string, attachmentId: string, fileName: string): Promise<void>;
}

export interface WorkspaceRepository
  extends
    ResumeRepository,
    SupportingDocumentRepository,
    JobRepository,
    JobGoalRepository,
    ApplicationRepository,
    ConversationRepository {
  getSnapshot(): Promise<WorkspaceSnapshot>;
  resetData(): Promise<WorkspaceSnapshot>;
}
