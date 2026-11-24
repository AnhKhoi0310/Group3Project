// Sprint 2: S2-017 switching the active target.
// Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
import { fireEvent, render, screen } from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useParams,
} from "react-router-dom";
import { createFakeApi } from "../test/fakeAuth";
import TargetSwitcher from "./TargetSwitcher";

const TARGETS = [
  {
    id: 1,
    name: "Example Cafe",
    platform: "google_maps",
    source_url: "https://example.com/cafe",
    created_at: "2026-11-10T00:00:00",
  },
  {
    id: 2,
    name: "Second Bakery",
    platform: "google_maps",
    source_url: "https://example.com/bakery",
    created_at: "2026-11-11T00:00:00",
  },
];

function CurrentPath() {
  const location = useLocation();

  return <p data-testid="current-path">{location.pathname}</p>;
}

function WorkspaceHarness({ api }: { api: ReturnType<typeof createFakeApi> }) {
  const { targetId } = useParams();
  const activeTarget = TARGETS.find((target) => String(target.id) === targetId);

  if (!activeTarget) {
    return <p>Target not found</p>;
  }

  return (
    <>
      <TargetSwitcher
        api={api}
        activeTargetId={activeTarget.id}
        activeTargetName={activeTarget.name}
      />
      <CurrentPath />
    </>
  );
}

function renderSwitcher(api = createFakeApi()) {
  render(
    <MemoryRouter initialEntries={["/targets/1"]}>
      <Routes>
        <Route
          path="/targets/:targetId"
          element={<WorkspaceHarness api={api} />}
        />
      </Routes>
    </MemoryRouter>,
  );

  return api;
}

describe("TargetSwitcher", () => {
  // S2-017: the switcher lists the user's own targets
  it("loads and displays the authenticated user's targets", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(TARGETS);

    renderSwitcher(api);

    expect(
      await screen.findByRole("option", { name: "Second Bakery" }),
    ).toBeInTheDocument();

    expect(screen.getByTestId("active-target-name")).toHaveTextContent(
      "Example Cafe",
    );

    expect(
      screen.getByRole("combobox", {
        name: "Switch active target",
      }),
    ).toHaveValue("1");

    expect(api.request).toHaveBeenCalledWith("/api/targets");
  });

  // S2-017: choosing a target opens it
  it("navigates to the selected owned target", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(TARGETS);

    renderSwitcher(api);

    const selector = await screen.findByRole("combobox", {
      name: "Switch active target",
    });

    fireEvent.change(selector, {
      target: { value: "2" },
    });

    expect(await screen.findByTestId("current-path")).toHaveTextContent(
      "/targets/2",
    );

    expect(screen.getByTestId("active-target-name")).toHaveTextContent(
      "Second Bakery",
    );
  });

  // S2-017: only the user's own targets are offered
  it("does not offer targets that are absent from the user's target list", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue([TARGETS[0]]);

    renderSwitcher(api);

    await screen.findByRole("combobox", {
      name: "Switch active target",
    });

    expect(
      screen.queryByRole("option", { name: "Second Bakery" }),
    ).not.toBeInTheDocument();

    expect(
      screen.getByRole("option", { name: "Example Cafe" }),
    ).toBeInTheDocument();
  });

  // S2-017: the active target stays visible if the list fails
  it("keeps the active target visible if loading the target list fails", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(new Error("Network failure"));

    renderSwitcher(api);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn't load your targets. Please try again.",
    );

    expect(screen.getByTestId("active-target-name")).toHaveTextContent(
      "Example Cafe",
    );

    expect(
      screen.getByRole("option", { name: "Example Cafe" }),
    ).toBeInTheDocument();
  });
});
