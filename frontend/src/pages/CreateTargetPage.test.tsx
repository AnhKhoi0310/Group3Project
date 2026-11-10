import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { ApiError } from "../api/client";
import { AuthProvider } from "../auth/AuthContext";
import { createFakeApi, createFakeAuth, USER_A } from "../test/fakeAuth";
import CreateTargetPage from "./CreateTargetPage";

const URL = "https://www.google.com/maps/place/Example+Cafe/data=!1s0x1:0x2";

function WorkspaceStub() {
  const location = useLocation();
  const created = (location.state as { created?: boolean } | null)?.created;
  return <p>Workspace opened{created ? " (created)" : ""}</p>;
}

function renderPage() {
  const api = createFakeApi();
  render(
    <MemoryRouter initialEntries={["/targets/new"]}>
      <AuthProvider client={createFakeAuth(USER_A)} api={api}>
        <Routes>
          <Route path="/targets/new" element={<CreateTargetPage />} />
          <Route path="/targets/:targetId" element={<WorkspaceStub />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
  return api;
}

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Create target" }));
}

describe("CreateTargetPage", () => {
  it("sends trimmed input and opens the new target's workspace", async () => {
    const api = renderPage();
    api.request.mockResolvedValue({
      id: 1,
      name: "Example Cafe",
      platform: "google_maps",
      source_url: URL,
      created_at: "2026-11-10T00:00:00",
    });

    fill("Business or product name", "  Example Cafe  ");
    fill("Google Maps link", ` ${URL} `);
    submit();

    expect(await screen.findByText("Workspace opened (created)")).toBeVisible();
    expect(api.request).toHaveBeenCalledWith(
      "/api/targets",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Example Cafe", source_url: URL }),
      }),
    );
  });

  it("shows backend field errors under the fields and keeps the input", async () => {
    const api = renderPage();
    api.request.mockRejectedValue(
      new ApiError(422, "validation_error", "Please correct the fields.", {
        source_url: "That doesn't look like a valid web address.",
      }),
    );

    fill("Business or product name", "Example Cafe");
    fill("Google Maps link", "nonsense");
    submit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That doesn't look like a valid web address.",
    );
    expect(screen.getByLabelText("Google Maps link")).toHaveValue("nonsense");
    expect(screen.getByLabelText("Google Maps link")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.queryByText(/Workspace opened/)).not.toBeInTheDocument();
  });

  it("shows a friendly message for server failures, never raw text", async () => {
    const api = renderPage();
    api.request.mockRejectedValue(new Error("SQL exploded: secret-sql"));

    fill("Business or product name", "Example Cafe");
    fill("Google Maps link", URL);
    submit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong on our side.",
    );
    expect(screen.queryByText(/secret-sql/)).not.toBeInTheDocument();
  });

  it("shows Google Maps as the fixed, read-only platform", () => {
    renderPage();

    expect(screen.getByLabelText("Platform")).toHaveValue("Google Maps");
    expect(screen.getByLabelText("Platform")).toHaveAttribute("readonly");
  });
});
