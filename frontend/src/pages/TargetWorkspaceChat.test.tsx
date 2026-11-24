// Sprint 2 extra: the docked chat in the workspace (tag: Chat dock).
// Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { QuestionAnswer } from "../api/questions";
import { AuthProvider } from "../auth/AuthContext";
import { FOCUS_REVIEW_EVENT } from "../components/ReviewList";
import { createFakeApi, createFakeAuth, USER_A } from "../test/fakeAuth";
import TargetWorkspacePage from "./TargetWorkspacePage";

const TARGET = {
  id: 1,
  name: "Joe's Pizza",
  platform: "google_maps",
  source_url: "https://www.google.com/maps/place/Joe's+Pizza/data=!1s0x1:0x2",
  created_at: "2026-11-10T00:00:00",
};

const REVIEW = {
  id: 7,
  target_id: 1,
  source_review_id: "r7",
  source_platform: "google_maps",
  reviewer_name: "Ana",
  rating: 5,
  text: "Crispy crust.",
  review_date: null,
  created_at: "2026-11-10T00:00:00",
  reviewer_avatar_url: null,
  image_urls: [],
};

const ANSWER: QuestionAnswer = {
  target_id: 1,
  target_name: "Joe's Pizza",
  status: "answered",
  answer: "The crust is the star.",
  reviews_used: 1,
  reviews_total: 1,
  evidence: [REVIEW],
};

function renderWorkspace() {
  const api = createFakeApi();
  api.request.mockImplementation(async (path: string) => {
    if (path === "/api/targets") return [TARGET];
    if (path === "/api/targets/1") return TARGET;
    if (path.endsWith("/ingestions/latest")) return null;
    if (path.endsWith("/summary")) {
      return {
        target_id: 1,
        target_name: "Joe's Pizza",
        review_count: 1,
        average_rating: 5,
        rating_distribution: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 1 },
      };
    }
    if (path.endsWith("/reviews")) return [REVIEW];
    if (path.endsWith("/questions")) return ANSWER;
    throw new Error(`Unexpected request ${path}`);
  });
  render(
    <MemoryRouter initialEntries={["/targets/1"]}>
      <AuthProvider client={createFakeAuth(USER_A)} api={api}>
        <Routes>
          <Route path="/targets/:targetId" element={<TargetWorkspacePage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
  return api;
}

function mockScreen(desktop: boolean) {
  window.matchMedia = vi.fn().mockReturnValue({ matches: desktop });
}

/** Questions open once the review count has loaded. */
async function askSuggestion() {
  await screen.findByRole("list", { name: "What ReviewLens can answer" });
  fireEvent.click(
    screen.getByRole("button", { name: "What do customers like most?" }),
  );
}

afterEach(() => {
  localStorage.clear();
  // @ts-expect-error jsdom has no matchMedia by default
  delete window.matchMedia;
});

// Chat dock: docked beside the workspace; hide and reopen
it("docks the chat beside the workspace, hides it and brings it back", async () => {
  renderWorkspace();
  expect(
    await screen.findByRole("heading", { name: "Ask about Joe's Pizza" }),
  ).toBeVisible();
  expect(screen.getByTestId("chat-dock")).toHaveAttribute("data-open", "true");

  fireEvent.click(screen.getByRole("button", { name: "Hide chat" }));

  expect(screen.getByTestId("chat-dock")).toHaveAttribute("data-open", "false");
  expect(JSON.parse(localStorage.getItem("reviewlens.chat")!)).toMatchObject({
    open: false,
  });

  fireEvent.click(screen.getByRole("button", { name: "Open ReviewLens chat" }));

  expect(screen.getByTestId("chat-dock")).toHaveAttribute("data-open", "true");
  expect(
    screen.queryByRole("button", { name: "Open ReviewLens chat" }),
  ).not.toBeInTheDocument();
});

// Chat dock: width is remembered and clamped
it("remembers the chat width and ignores broken saved settings", async () => {
  localStorage.setItem(
    "reviewlens.chat",
    JSON.stringify({ open: true, width: 9999 }),
  );
  renderWorkspace();

  const handle = await screen.findByRole("separator", { name: "Resize chat" });
  expect(handle).toHaveAttribute("aria-valuenow", "720");

  fireEvent.keyDown(handle, { key: "ArrowRight" });
  expect(JSON.parse(localStorage.getItem("reviewlens.chat")!).width).toBe(696);
});

// Chat dock: unreadable saved settings fall back to defaults
it("falls back to defaults when saved settings are unreadable", async () => {
  localStorage.setItem("reviewlens.chat", "{not json");
  renderWorkspace();

  expect(
    await screen.findByRole("separator", { name: "Resize chat" }),
  ).toHaveAttribute("aria-valuenow", "420");
});

// Chat dock: Show in reviews jumps to the review list
it("jumps from a cited review to the review list", async () => {
  mockScreen(true);
  const jumps: number[] = [];
  const listen = (event: Event) => jumps.push((event as CustomEvent).detail);
  window.addEventListener(FOCUS_REVIEW_EVENT, listen);
  try {
    renderWorkspace();
    await askSuggestion();
    fireEvent.click(
      await screen.findByRole("button", { name: "Show in reviews" }),
    );

    expect(jumps).toEqual([7]);
    expect(screen.getByTestId("chat-dock")).toHaveAttribute(
      "data-open",
      "true",
    );
  } finally {
    window.removeEventListener(FOCUS_REVIEW_EVENT, listen);
  }
});

// Chat dock: starts closed on small screens and steps aside
it("starts closed on small screens and steps aside when jumping to a review", async () => {
  mockScreen(false);
  renderWorkspace();

  await screen.findByRole("heading", { name: "Joe's Pizza", level: 1 });
  expect(screen.getByTestId("chat-dock")).toHaveAttribute("data-open", "false");

  fireEvent.click(screen.getByRole("button", { name: "Open ReviewLens chat" }));
  await askSuggestion();
  const showInReviews = await screen.findByRole("button", {
    name: "Show in reviews",
  });
  act(() => {
    fireEvent.click(showInReviews);
  });

  expect(screen.getByTestId("chat-dock")).toHaveAttribute("data-open", "false");
});
