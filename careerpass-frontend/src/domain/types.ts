export type UserRole = "candidate" | "hr";

export type ResumeParseStatus =
  "not_uploaded" | "uploading" | "processing" | "succeeded" | "failed";

export type AgentStatus = "not_started" | "ready" | "running" | "finished";
export type AgentRunState = "not_started" | "running" | "finished";

export interface AgentRunSummary {
  id: string;
  status: "running" | "finished";
  startedAt: string;
  finishedAt: string | null;
  finishReason: "offer_target_reached" | "no_match" | null;
}

export interface AgentRunStatus {
  state: AgentRunState;
  canStart: boolean;
  run: AgentRunSummary | null;
}

export type DeliveryProgress =
  | "submitted"
  | "screening"
  | "written_test"
  | "interview_1"
  | "interview_2"
  | "interview_3"
  | "hr_interview"
  | "offer"
  | "terminated";

export interface UserProfile {
  id: string;
  role: UserRole;
  displayName: string;
  title: string;
}

export interface Resume {
  id: string;
  fileName: string;
  uploadedAt: string;
  parseStatus: ResumeParseStatus;
  version: number;
  isCurrent?: boolean;
}

export interface SupportingDocument {
  id: string;
  fileName: string;
  fileType: "pdf" | "md" | "jpg" | "png";
  uploadedAt: string;
  status: "success";
}

export interface SupportingDocumentUploadResult {
  fileName: string;
  status: "ready" | "success" | "failed";
  result?: "created" | "duplicate" | "failed";
  document: SupportingDocument | null;
  failureCode: string | null;
}

export interface Job {
  id: string;
  fileName: string;
  uploadedAt: string;
  version: number;
  title: string;
  company: string;
  location: string;
  salary: string;
  summary: string;
  uploaded: boolean;
}

export type HrJobParseStatus = "queued" | "running" | "succeeded" | "failed";

export interface HrJob {
  id: string;
  fileName: string | null;
  jobTitle: string | null;
  companyName: string | null;
  createdAt: string;
  parseStatus: HrJobParseStatus | null;
  matchStarted?: boolean;
}

export interface JobGoal {
  id: string;
  offerTarget: number;
  title: string;
  filters: string;
  status?: "active" | "achieved" | "abandoned";
  createdAt: string;
  updatedAt?: string;
}

export interface Application {
  id: string;
  jobId: string;
  candidateId: string;
  jobTitle: string;
  company: string;
  location: string;
  salary: string;
  status: DeliveryProgress;
  appliedAt: string;
  lastContactAt: string | null;
  matchScore: number;
  recommendationReason: string;
}

export interface HrApplication {
  id: string;
  jobId: string;
  jobTitle: string;
  companyName: string | null;
  candidateName: string;
  status: DeliveryProgress;
}

export interface Message {
  id: string;
  sender: "hr" | "agent";
  text: string;
  createdAt: string;
  status?: "pending" | "sent" | "failed";
  messageType?: "text";
  attachments?: MessageAttachment[];
}

export type MessageAttachmentStatus = "preparing" | "downloadable" | "failed" | "expired";

export interface MessageAttachment {
  id: string;
  fileName: string;
  fileType: string;
  fileSizeBytes: number;
  createdAt: string;
  expiresAt: string;
  status: MessageAttachmentStatus;
}

export interface Conversation {
  id: string;
  applicationId: string;
  jobTitle: string;
  candidateName: string;
  messages: Message[];
}

export interface WorkspaceSnapshot {
  resume: Resume | null;
  supportingDocuments: SupportingDocument[];
  supportingDocumentUploads: SupportingDocumentUploadResult[];
  jobs: Job[];
  currentJob: Job | null;
  hrJobs: HrJob[];
  currentHrJob: HrJob | null;
  jobGoal: JobGoal | null;
  agentStatus: AgentStatus;
  round: number;
  applications: Application[];
  hrApplications: HrApplication[];
  conversations: Conversation[];
}

export interface JobGoalInput {
  offerTarget: number;
  title: string;
  filters: string;
}
