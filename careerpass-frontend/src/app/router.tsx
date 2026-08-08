import { createBrowserRouter, Navigate } from "react-router-dom";
import { AuthLayout } from "../layouts/AuthLayout";
import { CandidateRouteLayout, HrRouteLayout } from "../layouts/RoleRouteLayouts";
import { LoginPage } from "../pages/auth/LoginPage";
import { RegisterPage } from "../pages/auth/RegisterPage";
import { CandidateHomePage } from "../pages/candidate/CandidateHomePage";
import { DocumentsPage } from "../pages/candidate/DocumentsPage";
import { JobGoalPage } from "../pages/candidate/JobGoalPage";
import { ProgressPage } from "../pages/candidate/ProgressPage";
import { HrHomePage } from "../pages/hr/HrHomePage";
import { JobsPage } from "../pages/hr/JobsPage";
import { ConversationsPage } from "../pages/hr/ConversationsPage";
import { ApplicationsPage } from "../pages/hr/ApplicationsPage";

export const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    path: "/candidate",
    element: <CandidateRouteLayout />,
    children: [
      { index: true, element: <CandidateHomePage /> },
      { path: "documents", element: <DocumentsPage /> },
      { path: "job-goal", element: <JobGoalPage /> },
      { path: "progress", element: <ProgressPage /> },
      { path: "*", element: <Navigate to="/candidate" replace /> },
    ],
  },
  {
    path: "/hr",
    element: <HrRouteLayout />,
    children: [
      { index: true, element: <HrHomePage /> },
      { path: "jobs", element: <JobsPage /> },
      { path: "conversations", element: <ConversationsPage /> },
      { path: "applications", element: <ApplicationsPage /> },
      { path: "*", element: <Navigate to="/hr" replace /> },
    ],
  },
  { path: "/", element: <Navigate to="/login" replace /> },
  { path: "*", element: <Navigate to="/login" replace /> },
]);
