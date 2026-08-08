import type {
  Application,
  Conversation,
  DemoSnapshot,
  DeliveryProgress,
  Job,
  JobGoal,
  JobGoalInput,
  Resume,
  SupportingDocument,
} from "../../domain/types";

export interface ResumeRepository {
  getCurrentResume(): Promise<Resume | null>;
  uploadResume(file: File): Promise<Resume>;
  simulateParseResult(result: "succeeded" | "failed"): Promise<Resume>;
}

export interface SupportingDocumentRepository {
  listDocuments(): Promise<SupportingDocument[]>;
  uploadDocuments(files: File[]): Promise<SupportingDocument[]>;
}

export interface JobRepository {
  getCurrentJob(): Promise<Job | null>;
  uploadJob(file: File): Promise<Job>;
}

export interface JobGoalRepository {
  getCurrentGoal(): Promise<JobGoal | null>;
  saveGoal(input: JobGoalInput): Promise<JobGoal>;
  startAgent(): Promise<DemoSnapshot>;
}

export interface ApplicationRepository {
  listApplications(): Promise<Application[]>;
  updateApplicationStatus(id: string, status: DeliveryProgress): Promise<Application>;
}

export interface ConversationRepository {
  listConversations(): Promise<Conversation[]>;
  sendConversationMessage(id: string, content: string): Promise<Conversation>;
}

export interface DemoRepository
  extends
    ResumeRepository,
    SupportingDocumentRepository,
    JobRepository,
    JobGoalRepository,
    ApplicationRepository,
    ConversationRepository {
  getSnapshot(): Promise<DemoSnapshot>;
  resetDemo(): Promise<DemoSnapshot>;
}
