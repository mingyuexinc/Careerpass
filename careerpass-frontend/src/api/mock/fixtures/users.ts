import type { DemoUser } from "../../../domain/types";

export const demoUsers: DemoUser[] = [
  {
    id: "candidate-demo",
    role: "candidate",
    displayName: "Alex Chen",
    title: "求职者 Demo",
  },
  { id: "hr-demo", role: "hr", displayName: "Mia Wang", title: "HR Demo" },
];
