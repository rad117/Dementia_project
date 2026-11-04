import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ClinicalLogin from "./ClinicalLogin.jsx";
import { SessionProvider } from "../../app/SessionContext.jsx";

const { loginClinicalUserMock } = vi.hoisted(() => ({ loginClinicalUserMock: vi.fn() }));

vi.mock("../../services/index.js", () => ({
  loginClinicalUser: loginClinicalUserMock,
}));

const navigateMock = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => navigateMock };
});

function renderLogin() {
  return render(
    <MemoryRouter>
      <SessionProvider>
        <ClinicalLogin />
      </SessionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  loginClinicalUserMock.mockReset();
  navigateMock.mockReset();
});

describe("ClinicalLogin", () => {
  it("signs in and navigates to the dashboard on valid credentials", async () => {
    loginClinicalUserMock.mockResolvedValue({ token: "tok_123", name: "Dr. Sharma", role: "Clinical Professional" });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "dr.sharma@memora.org");
    await user.type(screen.getByLabelText(/password/i), "demo1234");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/clinical"));
    expect(loginClinicalUserMock).toHaveBeenCalledWith({
      email: "dr.sharma@memora.org",
      password: "demo1234",
    });
  });

  it("shows an error and does not navigate on invalid credentials", async () => {
    loginClinicalUserMock.mockRejectedValue(new Error("Invalid email or password."));
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "dr.sharma@memora.org");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
