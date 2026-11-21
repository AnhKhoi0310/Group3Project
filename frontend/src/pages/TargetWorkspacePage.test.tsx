import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ApiError } from "../api/client";
import type { ReviewSummary } from "../api/reviews";
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

const RESULT_PARTIAL = {
  target_id: 1,
  status: "succeeded",
  reviews_found: 12,
  reviews_skipped: 2,
  skipped_reasons: {
    missing_text: 1,
    invalid_rating: 1,
  },
};

const RESULT_SUCCEEDED = {
  target_id: 1,
  status: "succeeded",
  reviews_found: 12,
  reviews_skipped: 0,
};

const RESULT_EMPTY = {
  target_id: 1,
  status: "succeeded",
  reviews_found: 0,
  reviews_skipped: 0,
};

const EMPTY_SUMMARY = {
  target_id: 1,
  target_name: "Example Cafe",
  review_count: 0,
  average_rating: null,
  rating_distribution: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0 },
};

const POPULATED_SUMMARY = {
  target_id: 1,
  target_name: "Example Cafe",
  review_count: 4,
  average_rating: 4.3,
  rating_distribution: { "1": 0, "2": 0, "3": 1, "4": 1, "5": 2 },
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

/** GET target returns TARGET; GET latest ingestion returns latestAttempt; GET summary returns summary; POST runs ingest */
function apiWithState(
  latestAttempt: unknown = null,
  ingest?: () => Promise<unknown>,
  summary: unknown = EMPTY_SUMMARY,
) {
  const api = createFakeApi();
  api.request.mockImplementation(async (path: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      return ingest ? ingest() : RESULT_SUCCEEDED;
    }
    if (path.endsWith("/ingestions/latest")) {
      return latestAttempt;
    }
    if (path.endsWith("/summary")) {
      return summary;
    }
    if (path.endsWith("/reviews")) {
      return [];
    }
    return TARGET;
  });
  return api;
}

/** GET returns the target; POST (ingestion) runs the given behavior. */
function apiWithIngestion(ingest: () => Promise<unknown>) {
  return apiWithState(null, ingest);
}

async function openAndCollect(api: ReturnType<typeof createFakeApi>) {
  renderPage(api);
  fireEvent.click(
    await screen.findByRole("button", { name: "Collect reviews" }),
  );
}

describe("TargetWorkspacePage", () => {
  it("identifies the active target, platform, source and ingestion state", async () => {
    const api = apiWithState(null);
    renderPage(api);

    expect(
      await screen.findByRole("heading", { name: "Example Cafe" }),
    ).toBeVisible();
    expect(screen.getByText("Google Maps")).toBeVisible();
    expect(screen.getByText(TARGET.source_url)).toBeVisible();
    expect(screen.getByText("Not started")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Collect reviews" }),
    ).toBeEnabled();
    expect(api.request).toHaveBeenCalledWith("/api/targets/1");
  });

  it("shows a confirmation after a target was just created", async () => {
    const api = apiWithState(null);
    renderPage(api, { created: true });

    expect(await screen.findByText(/Target created/)).toBeVisible();
    expect(
      screen.getByText("Target created. It is saved to your account."),
    ).toHaveAttribute("role", "status");
  });

  it("shows no confirmation when opened normally", async () => {
    const api = apiWithState(null);
    renderPage(api);

    await screen.findByRole("heading", { name: "Example Cafe" });

    expect(screen.queryByText(/Target created/)).not.toBeInTheDocument();
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

describe("TargetWorkspacePage review collection", () => {
  it("starts ingestion for this target and shows a partial result when records are skipped", async () => {
    const api = apiWithIngestion(async () => RESULT_PARTIAL);
    await openAndCollect(api);

    expect(await screen.findByText(/Found 12 reviews/)).toBeVisible();
    expect(
      screen.getByText(
        /2 were skipped and excluded from the active dataset: 1 \(missing review text\), 1 \(invalid rating\)\./,
      ),
    ).toBeVisible();
    expect(screen.getByTestId("ingestion-status-badge")).toHaveTextContent(
      "Partial success",
    );
    expect(api.request).toHaveBeenCalledWith("/api/targets/1/ingestions", {
      method: "POST",
    });
  });

  it("reports malformed records, duplicate reviews, and singular skipped counts clearly", async () => {
    const api = apiWithState({
      target_id: 1,
      status: "succeeded",
      reviews_found: 1,
      reviews_skipped: 3,
      skipped_reasons: {
        malformed_record: 1,
        duplicate_record: 2,
      },
    });
    renderPage(api);

    expect(
      await screen.findByText(
        /Found 1 review\. 3 were skipped and excluded from the active dataset: 1 \(malformed source record\), 2 \(duplicate review\)\./,
      ),
    ).toBeVisible();
  });

  it("displays Partial success when ingestion finishes with zero usable reviews", async () => {
    const api = apiWithState(RESULT_EMPTY);
    renderPage(api);

    expect(
      await screen.findByTestId("ingestion-status-badge"),
    ).toHaveTextContent("Partial success");
    expect(
      screen.getByText(
        "Ingestion finished, but no usable reviews were added to the dataset.",
      ),
    ).toBeVisible();
  });

  it("disables the button and explains the wait while collecting", async () => {
    const api = apiWithIngestion(() => new Promise(() => {}));
    await openAndCollect(api);

    expect(
      await screen.findByRole("button", { name: "Collecting reviews…" }),
    ).toBeDisabled();
    expect(screen.getByText(/Ingestion is currently running/)).toBeVisible();
  });

  it("shows the backend's friendly message when collection fails", async () => {
    const api = apiWithIngestion(async () => {
      throw new ApiError(
        502,
        "ingestion_provider_unavailable",
        "We couldn't reach the review source. Try again in a few minutes.",
      );
    });
    await openAndCollect(api);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn't reach the review source.",
    );
    expect(screen.queryByText(/Found/)).not.toBeInTheDocument();
    expect(screen.getByText("Not started")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Collect reviews" }),
    ).toBeEnabled();
  });

  it("never shows raw error text when collection fails", async () => {
    const api = apiWithIngestion(async () => {
      throw new Error("SQL exploded: secret-sql");
    });
    await openAndCollect(api);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong on our side.",
    );
    expect(screen.queryByText(/secret-sql/)).not.toBeInTheDocument();
  });
});

describe("TargetWorkspacePage review summary", () => {
  it("displays the review count, average rating, and rating distribution for the active target", async () => {
    const api = apiWithState(RESULT_SUCCEEDED, undefined, POPULATED_SUMMARY);
    renderPage(api);

    expect(
      await screen.findByRole("heading", {
        name: "Review summary for Example Cafe",
      }),
    ).toBeVisible();
    expect(await screen.findByTestId("summary-review-count")).toHaveTextContent(
      "4",
    );
    expect(screen.getByTestId("summary-average-rating")).toHaveTextContent(
      "4.3 / 5",
    );
    expect(screen.getByText("5 ★").nextSibling).toHaveTextContent("2");
    expect(screen.getByText("4 ★").nextSibling).toHaveTextContent("1");
    expect(screen.getByText("3 ★").nextSibling).toHaveTextContent("1");
  });

  it("shows zero reviews and no ratings yet when no reviews have been ingested", async () => {
    const api = apiWithState(null, undefined, EMPTY_SUMMARY);
    renderPage(api);

    expect(await screen.findByTestId("summary-review-count")).toHaveTextContent(
      "0",
    );
    expect(screen.getByTestId("summary-average-rating")).toHaveTextContent(
      "No ratings yet",
    );
  });

  it("shows a safe error message if the review summary fails to load", async () => {
    const api = createFakeApi();
    api.request.mockImplementation(async (path: string) => {
      if (path.endsWith("/summary")) {
        throw new Error("DB connection failed: secret-db");
      }
      if (path.endsWith("/ingestions/latest")) {
        return null;
      }
      if (path.endsWith("/reviews")) {
        return [];
      }
      return TARGET;
    });
    renderPage(api);

    expect(
      await screen.findByText(
        "We couldn't load the review summary. Please try again.",
      ),
    ).toBeVisible();
    expect(screen.queryByText(/secret-db/)).not.toBeInTheDocument();
  });

  it("refreshes the summary from persisted backend data after ingestion completes", async () => {
    let currentSummary: ReviewSummary = EMPTY_SUMMARY;
    const api = createFakeApi();

    api.request.mockImplementation(async (path: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        currentSummary = POPULATED_SUMMARY;
        return RESULT_SUCCEEDED;
      }
      if (path.endsWith("/ingestions/latest")) {
        return null;
      }
      if (path.endsWith("/summary")) {
        return currentSummary;
      }
      if (path.endsWith("/reviews")) {
        return [];
      }
      return TARGET;
    });

    renderPage(api);

    expect(await screen.findByTestId("summary-review-count")).toHaveTextContent(
      "0",
    );
    expect(screen.getByTestId("summary-average-rating")).toHaveTextContent(
      "No ratings yet",
    );

    fireEvent.click(screen.getByRole("button", { name: "Collect reviews" }));

    await waitFor(() => {
      expect(screen.getByTestId("summary-review-count")).toHaveTextContent("4");
    });
    expect(screen.getByTestId("summary-average-rating")).toHaveTextContent(
      "4.3 / 5",
    );
  });

  it("updates the summary cleanly when switching to a different active target", async () => {
    const targetTwo = {
      ...TARGET,
      id: 2,
      name: "Second Bakery",
    };
    const summaryTwo = {
      target_id: 2,
      target_name: "Second Bakery",
      review_count: 1,
      average_rating: 2.0,
      rating_distribution: { "1": 0, "2": 1, "3": 0, "4": 0, "5": 0 },
    };

    const api = createFakeApi();
    api.request.mockImplementation(async (path: string) => {
      if (path === "/api/targets/1") return TARGET;
      if (path === "/api/targets/1/summary") return POPULATED_SUMMARY;
      if (path === "/api/targets/2") return targetTwo;
      if (path === "/api/targets/2/summary") return summaryTwo;
      if (path.endsWith("/ingestions/latest")) return null;
      if (path.endsWith("/reviews")) return [];
      return TARGET;
    });

    const { rerender } = render(
      <MemoryRouter key="/targets/1" initialEntries={["/targets/1"]}>
        <AuthProvider client={createFakeAuth(USER_A)} api={api}>
          <Routes>
            <Route
              path="/targets/:targetId"
              element={<TargetWorkspacePage />}
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("summary-review-count")).toHaveTextContent(
      "4",
    );

    rerender(
      <MemoryRouter key="/targets/2" initialEntries={["/targets/2"]}>
        <AuthProvider client={createFakeAuth(USER_A)} api={api}>
          <Routes>
            <Route
              path="/targets/:targetId"
              element={<TargetWorkspacePage />}
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Review summary for Second Bakery",
      }),
    ).toBeVisible();
    expect(await screen.findByTestId("summary-review-count")).toHaveTextContent(
      "1",
    );
    expect(screen.getByTestId("summary-average-rating")).toHaveTextContent(
      "2.0 / 5",
    );
  });
});
