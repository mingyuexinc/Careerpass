import type { UserProfile } from "../../../domain/types";

export const userFixtures: UserProfile[] = [
  {
    id: "candidate-001",
    role: "candidate",
    displayName: "Alex Chen",
    title: "求职者工作台",
  },
  { id: "hr-001", role: "hr", displayName: "Mia Wang", title: "HR 工作台" },
];
