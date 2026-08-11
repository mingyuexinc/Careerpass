import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RoleLayout } from "../layouts/RoleLayout";
import { LoginPage } from "../pages/auth/LoginPage";
import { useAuthStore } from "../stores/auth-store";

describe("LoginPage", () => {
  it("renders the role selector and login form", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "开始你的求职旅程" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "求职者" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "HR" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "登录" })).toBeInTheDocument();
  });

  it("switches the role and keeps the account input ready", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "HR" }));
    expect(screen.getByPlaceholderText("请输入账号")).toHaveValue("");
  });

  it("uses the backend login contract for a candidate account", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 0,
          msg: "success",
          data: {
            access_token: "token",
            token_type: "Bearer",
            expires_in: 1800,
            user: {
              user_id: "user-001",
              roles: ["candidate"],
              active_role: "candidate",
              candidate_id: "candidate-001",
              hr_profile_id: null,
              username: "candidate_01",
              name: "Alex Chen",
            },
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByPlaceholderText("请输入账号"), {
      target: { value: "candidate_01" },
    });
    fireEvent.change(screen.getByPlaceholderText("请输入密码"), {
      target: { value: "123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          username: "candidate_01",
          password: "123",
          active_role: "candidate",
        }),
      }),
    );
    fetchMock.mockRestore();
  });

  it.each([
    ["candidate", "求职者工作台"],
    ["hr", "HR 工作台"],
  ] as const)("renders the %s workspace identity badge", (role, label) => {
    act(() => useAuthStore.getState().signIn(role));
    const { container } = render(
      <MemoryRouter>
        <RoleLayout role={role}>
          <div>工作区内容</div>
        </RoleLayout>
      </MemoryRouter>,
    );
    expect(container.querySelector(".role-badge")).toHaveTextContent(label);
    expect(container.querySelector(".role-badge .dot")).toBeInTheDocument();
    expect(container.querySelector(".avatar")).toHaveTextContent(
      role === "candidate" ? "A" : "M",
    );
    expect(
      screen.getByText(role === "candidate" ? "Alex Chen" : "Mia Wang"),
    ).toBeInTheDocument();
    act(() => useAuthStore.getState().signOut());
  });

  it.each([
    ["candidate", ["使用指南", "求职资料上传", "求职任务创建", "求职进度查看"]],
    ["hr", ["使用指南", "岗位 JD 上传", "求职沟通", "投递进度更新"]],
  ] as const)(
    "matches the %s navigation labels from the HTML reference",
    (role, labels) => {
      const { container } = render(
        <MemoryRouter>
          <RoleLayout role={role}>
            <div>工作区内容</div>
          </RoleLayout>
        </MemoryRouter>,
      );
      expect(container.querySelector("nav")).toBeInTheDocument();
      labels.forEach((label) =>
        expect(screen.getByRole("link", { name: new RegExp(label) })).toBeInTheDocument(),
      );
    },
  );
});
