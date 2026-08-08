import { Outlet } from "react-router-dom";
import { RoleLayout } from "./RoleLayout";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth-store";

export function CandidateRouteLayout() {
  const user = useAuthStore((state) => state.user);
  if (!user || user.role !== "candidate") return <Navigate to="/login" replace />;
  return (
    <RoleLayout role="candidate">
      <Outlet />
    </RoleLayout>
  );
}

export function HrRouteLayout() {
  const user = useAuthStore((state) => state.user);
  if (!user || user.role !== "hr") return <Navigate to="/login" replace />;
  return (
    <RoleLayout role="hr">
      <Outlet />
    </RoleLayout>
  );
}
