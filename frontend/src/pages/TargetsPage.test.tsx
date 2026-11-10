import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ApiError } from "../api/client";
import { AuthProvider } from "../auth/AuthContext";
import { createFakeApi, createFakeAuth, USER_A } from "../test/fakeAuth";
import TargetsPage from "./TargetsPage";

const TARGET = {
  id: 1,
  name: "Example Cafe",
  platform: "google_maps",
  source_url: "https://www.google.com/maps/place/Example+Cafe/data=!1s0x1:0x2",
  created_at: "2026-11-10T00:00:00",
};

function renderPage(api = createFakeApi()) {
  render(
    <MemoryRouter>
      <AuthProvider client={createFakeAuth(USER_A)} api={api}>
        <TargetsPage />
      </AuthProvider>
    </MemoryRouter>,
  );
  return api;
}

describe("TargetsPage", () => {
  it("lists each target's name, platform and source", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue([TARGET]);
    renderPage(api);

    expect(await screen.findByText("Example Cafe")).toBeVisible();
    expect(screen.getByText("Google Maps")).toBeVisible();
    expect(screen.getByText(TARGET.source_url)).toBeVisible();
    expect(api.request).toHaveBeenCalledWith("/api/targets");
  });

  it("shows an empty state with a way to create a target", async () => {
    renderPage();

    expect(await screen.findByText(/don't have any targets yet/)).toBeVisible();
    expect(screen.getByRole("link", { name: "New target" })).toHaveAttribute(
      "href",
      "/targets/new",
    );
  });

  it("shows a loading indicator until targets arrive", () => {
    const api = createFakeApi();
    api.request.mockReturnValue(new Promise(() => {}));
    renderPage(api);

    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it("shows the backend's friendly message when loading fails", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(
      new ApiError(500, "unexpected", "Something went wrong on our side."),
    );
    renderPage(api);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong on our side.",
    );
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
