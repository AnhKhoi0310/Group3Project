// Sprint 2: S2-018 end-to-end target switch in the workspace (demo).
// Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import type { QuestionAnswer } from "../api/questions";
import { createFakeApi, createFakeAuth, USER_A } from "../test/fakeAuth";
import TargetWorkspacePage from "./TargetWorkspacePage";

const TARGET_A = {
  id: 1,
  name: "Battery Shop",
  platform: "google_maps",
  source_url: "https://example.com/battery-shop",
  created_at: "2026-11-10T00:00:00",
};

const TARGET_B = {
  id: 2,
  name: "Service Desk",
  platform: "google_maps",
  source_url: "https://example.com/service-desk",
  created_at: "2026-11-11T00:00:00",
};

const TARGETS = [TARGET_A, TARGET_B];

const SUMMARY_A = {
  target_id: 1,
  target_name: "Battery Shop",
  review_count: 4,
  average_rating: 4.5,
  rating_distribution: {
    "1": 0,
    "2": 0,
    "3": 0,
    "4": 2,
    "5": 2,
  },
};

const SUMMARY_B = {
  target_id: 2,
  target_name: "Service Desk",
  review_count: 2,
  average_rating: 2.0,
  rating_distribution: {
    "1": 0,
    "2": 2,
    "3": 0,
    "4": 0,
    "5": 0,
  },
};

const ANSWER_A: QuestionAnswer = {
  target_id: 1,
  target_name: "Battery Shop",
  status: "answered",
  answer: "Customers frequently praise the battery life.",
  reviews_used: 4,
  reviews_total: 4,
  evidence: [],
};

const ANSWER_B: QuestionAnswer = {
  target_id: 2,
  target_name: "Service Desk",
  status: "answered",
  answer: "Customers frequently mention customer service.",
  reviews_used: 2,
  reviews_total: 2,
  evidence: [],
};

describe("Target switching flow (S2-018)", () => {
  // S2-018 (demo): switching changes the target, summary and Q&A context
  it("switches the active target, summary, and subsequent Q&A context", async () => {
    const questionRequests: Array<{
      path: string;
      question: string;
    }> = [];

    let resolveTargetBSummary: (value: typeof SUMMARY_B) => void = () => {};

    const api = createFakeApi();

    api.request.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/targets") {
        return TARGETS;
      }

      if (path === "/api/targets/1") {
        return TARGET_A;
      }

      if (path === "/api/targets/2") {
        return TARGET_B;
      }

      if (path.endsWith("/ingestions/latest")) {
        return null;
      }

      if (path === "/api/targets/1/summary") {
        return SUMMARY_A;
      }

      if (path === "/api/targets/2/summary") {
        return new Promise<typeof SUMMARY_B>((resolve) => {
          resolveTargetBSummary = resolve;
        });
      }

      if (path.endsWith("/reviews")) {
        return [];
      }

      if (
        path === "/api/targets/1/questions" ||
        path === "/api/targets/2/questions"
      ) {
        const body = JSON.parse(String(init?.body)) as {
          question: string;
        };

        questionRequests.push({
          path,
          question: body.question,
        });

        return path === "/api/targets/1/questions" ? ANSWER_A : ANSWER_B;
      }

      throw new Error(`Unexpected API request: ${path}`);
    });

    render(
      <MemoryRouter initialEntries={["/targets/1"]}>
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

    // Initially Target A is active.
    expect(
      await screen.findByRole("heading", {
        name: "Battery Shop",
        level: 1,
      }),
    ).toBeVisible();

    expect(screen.getByTestId("active-target-name")).toHaveTextContent(
      "Battery Shop",
    );

    expect(await screen.findByTestId("summary-review-count")).toHaveTextContent(
      "4",
    );

    expect(screen.getByTestId("summary-average-rating")).toHaveTextContent(
      "4.5 / 5",
    );

    // Ask a question while Target A is active.
    fireEvent.change(screen.getByLabelText("Your question"), {
      target: { value: "What do customers say about battery life?" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Ask ReviewLens" }));

    expect(
      await screen.findByText("Customers frequently praise the battery life."),
    ).toBeVisible();

    expect(questionRequests).toContainEqual({
      path: "/api/targets/1/questions",
      question: "What do customers say about battery life?",
    });

    // Switch through the actual target selector.
    fireEvent.change(
      screen.getByRole("combobox", {
        name: "Switch active target",
      }),
      {
        target: { value: "2" },
      },
    );

    // The workspace now identifies Target B as active.
    expect(
      await screen.findByRole("heading", {
        name: "Service Desk",
        level: 1,
      }),
    ).toBeVisible();

    expect(screen.getByTestId("active-target-name")).toHaveTextContent(
      "Service Desk",
    );

    expect(
      screen.getByRole("heading", {
        name: "Ask about Service Desk",
      }),
    ).toBeVisible();

    // The previous target's Q&A response must not remain visible.
    expect(
      screen.queryByText("Customers frequently praise the battery life."),
    ).not.toBeInTheDocument();

    // The previous target's summary must not appear under Target B.
    await waitFor(() => {
      expect(resolveTargetBSummary).not.toBe(undefined);
    });

    expect(screen.getByText("Loading review summary…")).toBeVisible();

    expect(
      screen.queryByTestId("summary-review-count"),
    ).not.toBeInTheDocument();

    // Complete Target B's summary request.
    resolveTargetBSummary(SUMMARY_B);

    expect(await screen.findByTestId("summary-review-count")).toHaveTextContent(
      "2",
    );

    expect(screen.getByTestId("summary-average-rating")).toHaveTextContent(
      "2.0 / 5",
    );

    // Ask a new question. It must use Target B's endpoint.
    fireEvent.change(screen.getByLabelText("Your question"), {
      target: {
        value: "What do customers say about customer service?",
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "Ask ReviewLens" }));

    expect(
      await screen.findByText("Customers frequently mention customer service."),
    ).toBeVisible();

    expect(questionRequests).toContainEqual({
      path: "/api/targets/2/questions",
      question: "What do customers say about customer service?",
    });

    expect(api.request).toHaveBeenCalledWith("/api/targets/2/summary");
  });
});
