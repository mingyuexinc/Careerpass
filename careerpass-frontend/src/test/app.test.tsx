import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "../pages/auth/LoginPage";

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
});
