// Sprint 2: S2-020 empty target in the full workspace.
// Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { createFakeApi, createFakeAuth, USER_A } from "../test/fakeAuth";
import TargetWorkspacePage from "./TargetWorkspacePage";

const TARGET = {
  id: 1,
  name: "Joe's Pizza",
  platform: "google_maps",
  source_url: "https://www.google.com/maps/place/Joe's+Pizza/data=!1s0x1:0x2",
  created_at: "2026-11-10T00:00:00",
};

function summary(count: number) {
  return {
    target_id: 1,
    target_name: "Joe's Pizza",
    review_count: count,
    average_rating: count ? 4.5 : null,
    rating_distribution: { "1": 0, "2": 0, "3": 0, "4": count, "5": 0 },
  };
}

/** S2-020: a target without reviews can't be asked questions until collection. */
// S2-020 (demo extra): questions open only after reviews are collected
it("opens questions only after reviews are collected from the empty state", async () => {
  let collected = false;
  const api = createFakeApi();
  api.request.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === "/api/targets") return [TARGET];
    if (path === "/api/targets/1") return TARGET;
    if (path.endsWith("/ingestions/latest")) return null;
    if (path.endsWith("/ingestions") && init?.method === "POST") {
      collected = true;
      return {
        attempt_id: 1,
        target_id: 1,
        status: "succeeded",
        reviews_found: 3,
        reviews_skipped: 0,
      };
    }
    if (path.endsWith("/summary")) return summary(collected ? 3 : 0);
    if (path.endsWith("/reviews")) return [];
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

  expect(await screen.findByText("No reviews to analyze yet")).toBeVisible();
  expect(screen.getByLabelText("Your question")).toBeDisabled();
  expect(await screen.findByText("No customer photos yet")).toBeVisible();

  fireEvent.click(screen.getByRole("button", { name: "Collect reviews now" }));

  expect(
    await screen.findByRole("list", { name: "What ReviewLens can answer" }),
  ).toHaveTextContent("Answers from 3 Google Maps reviews of Joe's Pizza");
  expect(screen.getByLabelText("Your question")).toBeEnabled();
  expect(
    screen.queryByText("No reviews to analyze yet"),
  ).not.toBeInTheDocument();
  expect(api.request).toHaveBeenCalledWith(
    "/api/targets/1/ingestions",
    expect.objectContaining({ method: "POST" }),
  );
});
