import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { ApiError } from "./api/client";
import { AuthProvider } from "./auth/AuthContext";
import type { AuthUser } from "./auth/authClient";
import { createFakeApi, createFakeAuth, USER_A } from "./test/fakeAuth";

function renderApp(
  user: AuthUser | null | undefined,
  path = "/targets",
  api = createFakeApi(),
) {
  const client = createFakeAuth(user);
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider client={client} api={api}>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
  return { client, api };
}

describe("protected routes", () => {
  it("redirects a signed-out visitor to login without calling the API", () => {
    const { api } = renderApp(null);

    expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
    expect(screen.queryByText("Your targets")).not.toBeInTheDocument();
    expect(api.request).not.toHaveBeenCalled();
  });

  it("shows neither page content nor login while the session is loading", () => {
    renderApp(undefined);

    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(screen.queryByText("Your targets")).not.toBeInTheDocument();
    expect(screen.queryByText("Log in")).not.toBeInTheDocument();
  });

  it("shows a signed-in user the page and their backend-verified identity", async () => {
    const { api } = renderApp(USER_A);

    expect(screen.getByText("Your targets")).toBeInTheDocument();
    expect(await screen.findByText(/Verified as a@example.com/)).toBeVisible();
    expect(api.request).toHaveBeenCalledWith("/api/me");
  });

  it("shows the backend's friendly message when the API rejects the session", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(
      new ApiError(401, "unauthenticated", "Please log in to continue."),
    );

    renderApp(USER_A, "/targets", api);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Please log in to continue.",
    );
    expect(screen.queryByText(/Verified as/)).not.toBeInTheDocument();
  });

  it("sends an already signed-in user away from login", async () => {
    renderApp(USER_A, "/login");

    expect(await screen.findByText(/Verified as/)).toBeVisible();
  });

  it("sends unknown paths through the guard", () => {
    renderApp(null, "/nowhere");

    expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });
});

describe("logout", () => {
  it("revokes on the server, signs out, and returns to login", async () => {
    const { client, api } = renderApp(USER_A);

    fireEvent.click(screen.getByRole("button", { name: "Log out" }));

    expect(
      await screen.findByRole("heading", { name: "Log in" }),
    ).toBeInTheDocument();
    expect(api.request).toHaveBeenCalledWith("/api/auth/logout", {
      method: "POST",
    });
    expect(client.signOut).toHaveBeenCalledOnce();
  });

  it("still signs out locally when server revocation fails", async () => {
    const { client, api } = renderApp(USER_A);
    api.request.mockRejectedValue(new ApiError(503, "auth_unavailable", "x"));

    fireEvent.click(screen.getByRole("button", { name: "Log out" }));

    await waitFor(() => expect(client.signOut).toHaveBeenCalledOnce());
    expect(
      await screen.findByRole("heading", { name: "Log in" }),
    ).toBeInTheDocument();
  });
});
