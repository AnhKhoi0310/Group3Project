import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ApiError } from "../api/client";
import { AuthProvider } from "../auth/AuthContext";
import { createFakeApi, createFakeAuth, USER_A } from "../test/fakeAuth";
import TargetWorkspacePage from "./TargetWorkspacePage";

const TARGET = {
  id: 1,
  name: "Example Cafe",
  platform: "google_maps",
  source_url: "https://www.google.com/maps/place/Example+Cafe/data=!1s0x1:0x2",
  created_at: "2026-11-10T00:00:00",
};

function renderPage(api = createFakeApi(), state?: { created: boolean }) {
  render(
    <MemoryRouter initialEntries={[{ pathname: "/targets/1", state }]}>
      <AuthProvider client={createFakeAuth(USER_A)} api={api}>
        <Routes>
          <Route path="/targets/:targetId" element={<TargetWorkspacePage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
  return api;
}

describe("TargetWorkspacePage", () => {
  it("identifies the active target, platform, source and ingestion state", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(TARGET);
    renderPage(api);

    expect(
      await screen.findByRole("heading", { name: "Example Cafe" }),
    ).toBeVisible();
    expect(screen.getByText("Google Maps")).toBeVisible();
    expect(screen.getByText(TARGET.source_url)).toBeVisible();
    expect(screen.getByText("Not started")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Collect reviews" }),
    ).toBeDisabled();
    expect(api.request).toHaveBeenCalledWith("/api/targets/1");
  });

  it("shows a confirmation after a target was just created", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(TARGET);
    renderPage(api, { created: true });

    expect(await screen.findByText(/Target created/)).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Target created");
  });

  it("shows no confirmation when opened normally", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(TARGET);
    renderPage(api);

    await screen.findByRole("heading", { name: "Example Cafe" });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows a loading indicator until the target arrives", () => {
    const api = createFakeApi();
    api.request.mockReturnValue(new Promise(() => {}));
    renderPage(api);

    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it("shows the backend's message and no target data when access is denied", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(
      new ApiError(
        404,
        "target_not_found",
        "We couldn't find that target. It may not exist or you may not have access.",
      ),
    );
    renderPage(api);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn't find that target.",
    );
    expect(screen.queryByText("Example Cafe")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Collect reviews" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Back to your targets" }),
    ).toHaveAttribute("href", "/targets");
  });

  it("never shows raw error text", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(new Error("SQL exploded: secret-sql"));
    renderPage(api);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong on our side.",
    );
    expect(screen.queryByText(/secret-sql/)).not.toBeInTheDocument();
  });
});
