
import { fireEvent, render, screen } from "@testing-library/react";
import { ApiError } from "../api/client";
import type { QuestionAnswer } from "../api/questions";
import { createFakeApi } from "../test/fakeAuth";
import QuestionPanel from "./QuestionPanel";

function answer(overrides: Partial<QuestionAnswer> = {}): QuestionAnswer {
  return {
    target_id: 1,
    target_name: "Example Cafe",
    status: "answered",
    answer: "Customers love the espresso.",
    reviews_used: 2,
    reviews_total: 2,
    evidence: [
      {
        id: 7,
        rating: 5,
        text: "Best espresso in town.",
        reviewer_name: "Sam",
        review_date: null,
      },
    ],
    ...overrides,
  };
}

function renderPanel(api = createFakeApi()) {
  render(
    <QuestionPanel
      api={api}
      targetId="1"
      targetName="Example Cafe"
      reviewCount={2}
    />,
  );
  return api;
}

function ask(text: string) {
  fireEvent.change(screen.getByLabelText("Your question"), {
    target: { value: text },
  });
  fireEvent.click(screen.getByRole("button", { name: "Ask ReviewLens" }));
}

describe("QuestionPanel", () => {
  it("names the active target", () => {
    renderPanel();

    expect(
      screen.getByRole("heading", { name: "Ask about Example Cafe" }),
    ).toBeVisible();
  });

  it("sends the trimmed question and shows the answer with its evidence", async () => {
    const api = createFakeApi();
    let resolve: (value: QuestionAnswer) => void = () => {};
    api.request.mockReturnValue(new Promise((r) => (resolve = r)));
    renderPanel(api);

    ask("  What do people like?  ");

    expect(
      screen.getByRole("button", { name: "Reading the reviews…" }),
    ).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Reading the reviews for Example Cafe",
    );
    expect(api.request).toHaveBeenCalledWith("/api/targets/1/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "What do people like?" }),
    });

    resolve(answer());

    expect(
      await screen.findByText("Customers love the espresso."),
    ).toBeVisible();
    expect(screen.getByTestId("qa-status")).toHaveTextContent(
      "Answer from the reviews",
    );
    expect(
      screen.getByText("Based on 2 reviews for Example Cafe."),
    ).toBeVisible();
    expect(screen.getByText("Best espresso in town.")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Ask ReviewLens" }),
    ).toBeEnabled();
  });

  it("makes a lack of evidence clear", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(
      answer({
        status: "insufficient_evidence",
        answer: "The reviews don't mention parking.",
        evidence: [],
      }),
    );
    renderPanel(api);

    ask("Is parking safe at night?");

    expect(await screen.findByTestId("qa-status")).toHaveTextContent(
      "Not enough evidence in the reviews",
    );
    expect(
      screen.queryByText("Reviews this answer is based on"),
    ).not.toBeInTheDocument();
  });

  it("says when there are no successfully ingested reviews", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(
      answer({
        status: "insufficient_evidence",
        answer:
          "No successfully ingested reviews are available for this target. Complete a successful review ingestion before asking ReviewLens questions.",
        reviews_used: 0,
        reviews_total: 0,
        evidence: [],
      }),
    );
    renderPanel(api);

    ask("What do people like?");

    expect(await screen.findByTestId("qa-status")).toHaveTextContent(
      "No reviews to analyze yet",
    );
    expect(
      await screen.findByText(
        "No successfully ingested reviews are available for this target. Complete a successful review ingestion before asking ReviewLens questions.",
      ),
    ).toBeVisible();
    expect(screen.queryByText(/^Based on/)).not.toBeInTheDocument();
  });

  it("labels a declined question as out of scope", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(
      answer({
        status: "declined",
        answer: "I can only discuss these reviews.",
        evidence: [],
      }),
    );
    renderPanel(api);

    ask("Who is the president?");

    expect(await screen.findByTestId("qa-status")).toHaveTextContent(
      "Outside ReviewLens's scope",
    );
  });

  it("notes when only the most recent reviews were used", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(
      answer({ reviews_used: 200, reviews_total: 260 }),
    );
    renderPanel(api);

    ask("What do people like?");

    expect(
      await screen.findByText(
        "Based on the 200 most recent of 260 reviews for Example Cafe.",
      ),
    ).toBeVisible();
  });

  it("asks for a question instead of sending a blank one", () => {
    const api = renderPanel();

    ask("   ");

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Type a question about this target's reviews.",
    );
    expect(screen.getByLabelText("Your question")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(api.request).not.toHaveBeenCalled();
  });

  it("shows the server's field message on the question", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(
      new ApiError(422, "validation_error", "Please correct the fields.", {
        question: "Use 1000 characters or fewer.",
      }),
    );
    renderPanel(api);

    ask("Too long");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Use 1000 characters or fewer.",
    );
  });

  it("shows a friendly error when the AI request fails", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(
      new ApiError(504, "qa_timeout", "ReviewLens took too long to answer."),
    );
    renderPanel(api);

    ask("What do people like?");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "ReviewLens took too long to answer.",
    );
    expect(screen.queryByTestId("qa-result")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Ask ReviewLens" }),
    ).toBeEnabled();
  });

  it("falls back to a generic message for unexpected failures", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(new Error("boom"));
    renderPanel(api);

    ask("What do people like?");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "ReviewLens couldn't answer that right now. Please try again.",
    );
  });

  it("shortens very long evidence reviews", async () => {
    const api = createFakeApi();
    const long = "a".repeat(400);
    api.request.mockResolvedValue(
      answer({
        evidence: [
          {
            id: 1,
            rating: 4,
            text: long,
            reviewer_name: null,
            review_date: null,
          },
        ],
      }),
    );
    renderPanel(api);

    ask("What do people like?");

    expect(await screen.findByText(`${"a".repeat(220)}…`)).toBeVisible();
    expect(screen.getByText(/Anonymous/)).toBeVisible();
  });
});
