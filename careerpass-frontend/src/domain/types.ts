export type UserRole = "candidate" | "hr";

export type ResumeParseStatus =
  "not_uploaded" | "uploading" | "processing" | "succeeded" | "failed";

export type AgentStatus = "not_started" | "ready" | "running" | "finished";

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
}

export interface SupportingDocument {
  id: string;
  fileName: string;
  kind: "certificate" | "portfolio" | "other";
  uploadedAt: string;
  version: number;
  status: "uploading" | "ready" | "failed";
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

export interface JobGoal {
  id: string;
  offerTarget: number;
  title: string;
  filters: string;
  createdAt: string;
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
}

export interface Message {
  id: string;
  sender: "hr" | "agent";
  text: string;
  createdAt: string;
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
  jobs: Job[];
  currentJob: Job | null;
  jobGoal: JobGoal | null;
  agentStatus: AgentStatus;
  round: number;
  applications: Application[];
  conversations: Conversation[];
}

export interface JobGoalInput {
  offerTarget: number;
  title: string;
  filters: string;
}
