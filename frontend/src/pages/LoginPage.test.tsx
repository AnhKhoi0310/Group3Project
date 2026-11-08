import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { createFakeApi, createFakeAuth } from "../test/fakeAuth";
import LoginPage from "./LoginPage";

function renderLogin(from?: string) {
  const client = createFakeAuth(null);
  render(
    <MemoryRouter initialEntries={[{ pathname: "/login", state: { from } }]}>
      <AuthProvider client={client} api={createFakeApi()}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/targets" element={<p>Targets page</p>} />
          <Route path="/targets/7" element={<p>Target seven</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
  return client;
}

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function submit(name: string) {
  fireEvent.click(screen.getByRole("button", { name }));
}

describe("LoginPage", () => {
  it("logs in and continues to the targets page", async () => {
    const client = renderLogin();

    fill("Email", "a@example.com");
    fill("Password", "secret-pass");
    submit("Log in");

    expect(await screen.findByText("Targets page")).toBeInTheDocument();
    expect(client.signIn).toHaveBeenCalledWith("a@example.com", "secret-pass");
  });

  it("returns to the page the user originally asked for", async () => {
    renderLogin("/targets/7");

    fill("Email", "a@example.com");
    fill("Password", "secret-pass");
    submit("Log in");

    expect(await screen.findByText("Target seven")).toBeInTheDocument();
  });

  it("shows a user-friendly message for bad credentials", async () => {
    const client = renderLogin();
    client.signIn.mockRejectedValue({
      code: "auth/invalid-credential",
      message: "Firebase: Error (auth/invalid-credential).",
    });

    fill("Email", "a@example.com");
    fill("Password", "wrong");
    submit("Log in");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That email or password is incorrect.",
    );
    expect(screen.queryByText(/Firebase/)).not.toBeInTheDocument();
  });

  it("never shows raw provider text for an unknown error", async () => {
    const client = renderLogin();
    client.signIn.mockRejectedValue(new Error("internal provider detail"));

    fill("Email", "a@example.com");
    fill("Password", "secret-pass");
    submit("Log in");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn't sign you in.",
    );
    expect(screen.queryByText(/internal provider/)).not.toBeInTheDocument();
  });

  it("registers a new account", async () => {
    const client = renderLogin();

    fireEvent.click(screen.getByRole("button", { name: "Create an account" }));
    fill("Email", "new@example.com");
    fill("Password", "secret-pass");
    submit("Create account");

    expect(await screen.findByText("Targets page")).toBeInTheDocument();
    expect(client.register).toHaveBeenCalledWith(
      "new@example.com",
      "secret-pass",
    );
  });

  it("explains a duplicate email during registration", async () => {
    const client = renderLogin();
    client.register.mockRejectedValue({ code: "auth/email-already-in-use" });

    fireEvent.click(screen.getByRole("button", { name: "Create an account" }));
    fill("Email", "a@example.com");
    fill("Password", "secret-pass");
    submit("Create account");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "already exists",
    );
  });

  it("sends a password reset email", async () => {
    const client = renderLogin();

    fireEvent.click(screen.getByRole("button", { name: "Forgot password?" }));
    fill("Email", "a@example.com");
    submit("Send reset email");

    expect(await screen.findByRole("status")).toHaveTextContent("reset link");
    expect(client.resetPassword).toHaveBeenCalledWith("a@example.com");
  });
});
