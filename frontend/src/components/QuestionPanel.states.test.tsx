// Sprint 2: S2-020 chat readiness and S2-009 chat interactions.
// Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { ApiError } from "../api/client";
import type { QuestionAnswer } from "../api/questions";
import { createFakeApi } from "../test/fakeAuth";
import QuestionPanel, { SUGGESTED_QUESTIONS } from "./QuestionPanel";

const PHOTO = "https://lh3.googleusercontent.com/p1";

function answer(overrides: Partial<QuestionAnswer> = {}): QuestionAnswer {
  return {
    target_id: 1,
    target_name: "Joe's Pizza",
    status: "answered",
    answer: "People love the crispy crust.",
    reviews_used: 3,
    reviews_total: 3,
    evidence: [
      {
        id: 1,
        rating: 5,
        text: "Crispy crust, perfect slice.",
        reviewer_name: "Ana",
        review_date: null,
        reviewer_avatar_url: null,
        image_urls: [PHOTO],
      },
    ],
    ...overrides,
  };
}

function renderPanel(
  props: Partial<Parameters<typeof QuestionPanel>[0]> = {},
  api = createFakeApi(),
) {
  render(
    <QuestionPanel
      api={api}
      targetId="1"
      targetName="Joe's Pizza"
      reviewCount={3}
      {...props}
    />,
  );
  return api;
}

const input = () => screen.getByLabelText("Your question");

describe("QuestionPanel readiness (S2-020)", () => {
  // S2-020: no reviews disables questions and offers Collect reviews
  it("turns questions off and offers collection when there are no reviews", () => {
    const onCollect = vi.fn();
    const api = renderPanel({ reviewCount: 0, onCollect });

    expect(screen.getByText("No reviews to analyze yet")).toBeVisible();
    expect(input()).toBeDisabled();
    expect(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[0] }),
    ).toBeDisabled();
    expect(
      screen.queryByRole("list", { name: "What ReviewLens can answer" }),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Collect reviews now" }),
    );

    expect(onCollect).toHaveBeenCalledTimes(1);
    expect(api.request).not.toHaveBeenCalled();
  });

  // S2-020: questions stay off while collecting
  it("keeps questions off while reviews are being collected", () => {
    renderPanel({ reviewCount: 0, collecting: true });

    expect(screen.getByRole("status")).toHaveTextContent(
      "Collecting reviews for Joe's Pizza",
    );
    expect(input()).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Collect reviews now" }),
    ).not.toBeInTheDocument();
  });

  // S2-020: questions wait for the review count
  it("waits for the review count before allowing questions", () => {
    renderPanel({ reviewCount: "loading" });

    expect(screen.getByText("Checking the review dataset…")).toBeVisible();
    expect(input()).toBeDisabled();
  });

  // S2-009: the chat shows its scope once reviews exist
  it("shows what it can and can't answer once reviews exist", () => {
    renderPanel({ reviewCount: 1, platformLabel: "Google Maps" });

    const scope = screen.getByRole("list", {
      name: "What ReviewLens can answer",
    });
    expect(scope).toHaveTextContent("Answers from 1 Google Maps review");
    expect(scope).toHaveTextContent("Other review sites");
    expect(input()).toBeEnabled();
  });

  // S2-020: an unknown review count disables questions
  it("disables questions and displays an unavailable message when the review count is unknown", () => {
    const api = renderPanel({ reviewCount: null });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "ReviewLens couldn't determine whether reviews are available for Joe's Pizza.",
    );

    expect(input()).toBeDisabled();

    expect(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[0] }),
    ).toBeDisabled();

    expect(
      screen.getByRole("button", { name: "Ask ReviewLens" }),
    ).toBeDisabled();

    expect(
      screen.queryByRole("list", { name: "What ReviewLens can answer" }),
    ).not.toBeInTheDocument();

    expect(api.request).not.toHaveBeenCalled();
  });
});

describe("QuestionPanel interactions", () => {
  // S2-009: a suggested question asks in one click
  it("asks a suggested question with one click", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(answer());
    renderPanel({}, api);

    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[1] }),
    );

    expect(
      await screen.findByText("People love the crispy crust."),
    ).toBeVisible();
    expect(api.request).toHaveBeenCalledWith(
      "/api/targets/1/questions",
      expect.objectContaining({
        body: JSON.stringify({ question: SUGGESTED_QUESTIONS[1] }),
      }),
    );
  });

  // S2-009: Enter asks; Shift+Enter adds a line
  it("asks with Enter and keeps Shift+Enter for new lines", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(answer());
    renderPanel({}, api);
    fireEvent.change(input(), { target: { value: "What about the crust?" } });

    fireEvent.keyDown(input(), { key: "Enter", shiftKey: true });
    expect(api.request).not.toHaveBeenCalled();

    fireEvent.keyDown(input(), { key: "Enter" });

    expect(
      await screen.findByText("People love the crispy crust."),
    ).toBeVisible();
    expect(input()).toHaveValue("");
    expect(screen.getByText("What about the crust?")).toBeVisible();
  });

  // S2-009: a character counter shows the limit
  it("counts characters as you type", () => {
    renderPanel();

    fireEvent.change(input(), { target: { value: "Hello" } });

    expect(screen.getByText("5 / 1000")).toBeVisible();
  });

  // S2-009: questions list in order and can be cleared
  it("lists questions in conversation order and can clear them", async () => {
    const api = createFakeApi();
    api.request
      .mockResolvedValueOnce(answer({ answer: "First answer." }))
      .mockResolvedValueOnce(answer({ answer: "Second answer." }));
    renderPanel({}, api);

    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[0] }),
    );
    await screen.findByText("First answer.");
    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[2] }),
    );
    await screen.findByText("Second answer.");

    const results = screen.getAllByTestId("qa-result");
    expect(results[0]).toHaveTextContent("First answer.");
    expect(results[1]).toHaveTextContent("Second answer.");

    fireEvent.click(screen.getByRole("button", { name: "Clear questions" }));

    expect(screen.queryByTestId("qa-result")).not.toBeInTheDocument();
  });

  // S2-009: a service failure is its own outcome, with Try again
  it("shows a service failure as its own outcome and retries it", async () => {
    const api = createFakeApi();
    api.request
      .mockRejectedValueOnce(
        new ApiError(
          503,
          "qa_unavailable",
          "ReviewLens can't reach its AI service.",
        ),
      )
      .mockResolvedValueOnce(answer());
    renderPanel({}, api);

    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[0] }),
    );

    const failure = await screen.findByRole("alert");
    expect(failure).toHaveTextContent("ReviewLens couldn't answer");
    expect(failure).toHaveTextContent("ReviewLens can't reach its AI service.");

    fireEvent.click(within(failure).getByRole("button", { name: "Try again" }));

    expect(
      await screen.findByText("People love the crispy crust."),
    ).toBeVisible();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(api.request).toHaveBeenCalledTimes(2);
  });

  // S2-009: a rejected question is put back for editing
  it("puts the question back when the server rejects it", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(
      new ApiError(422, "validation_error", "Fix it.", {
        question: "Use 1000 characters or fewer.",
      }),
    );
    renderPanel({}, api);
    fireEvent.change(input(), { target: { value: "Too long question" } });

    fireEvent.click(screen.getByRole("button", { name: "Ask ReviewLens" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Use 1000 characters or fewer.",
    );
    expect(input()).toHaveValue("Too long question");
    expect(screen.queryByText("Your questions about Joe's Pizza")).toBeNull();
  });

  // S2-011: an answer can be copied
  it("copies an answer", async () => {
    const writeText = vi.fn(async () => {});
    Object.assign(navigator, { clipboard: { writeText } });
    const api = createFakeApi();
    api.request.mockResolvedValue(answer());
    renderPanel({}, api);
    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[0] }),
    );
    await screen.findByText("People love the crispy crust.");

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    });

    expect(writeText).toHaveBeenCalledWith("People love the crispy crust.");
    expect(screen.getByRole("button", { name: "Copied" })).toBeVisible();
  });

  // S2-011: three cited reviews show first, the rest on request
  it("shows three cited reviews first and the rest on request", async () => {
    const api = createFakeApi();
    const evidence = [1, 2, 3, 4, 5].map((id) => ({
      ...answer().evidence[0],
      id,
      text: `Cited review ${id}`,
      image_urls: [],
    }));
    api.request.mockResolvedValue(answer({ evidence }));
    renderPanel({}, api);
    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[0] }),
    );
    await screen.findByText("Cited review 3");

    expect(screen.queryByText("Cited review 4")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Show all 5 cited reviews" }),
    );
    expect(screen.getByText("Cited review 5")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Show fewer reviews" }));
    expect(screen.queryByText("Cited review 5")).not.toBeInTheDocument();
  });

  // Photos: a cited review's photo opens full size
  it("opens a cited review's photo full size", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(answer());
    renderPanel({}, api);
    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[0] }),
    );
    await screen.findByText("Crispy crust, perfect slice.");

    fireEvent.click(
      screen.getByRole("button", { name: "Open photo 1 of 1 from Ana" }),
    );

    const dialog = screen.getByRole("dialog", { name: "Photo 1 of 1" });
    expect(within(dialog).getByRole("img")).toHaveAttribute("src", PHOTO);
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  // S2-012, S2-014: each outcome has its own icon and label
  it("marks declined and insufficient-evidence outcomes with icons and labels", async () => {
    const api = createFakeApi();
    api.request
      .mockResolvedValueOnce(
        answer({ status: "declined", answer: "Out of scope.", evidence: [] }),
      )
      .mockResolvedValueOnce(
        answer({
          status: "insufficient_evidence",
          answer: "No info.",
          evidence: [],
        }),
      );
    renderPanel({}, api);

    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[0] }),
    );
    await screen.findByText("Out of scope.");
    fireEvent.click(
      screen.getByRole("button", { name: SUGGESTED_QUESTIONS[1] }),
    );
    await screen.findByText("No info.");

    const [older, newest] = screen.getAllByTestId("qa-status");
    expect(newest).toHaveTextContent("Not enough evidence in the reviews");
    expect(older).toHaveTextContent("Outside ReviewLens's scope");
    expect(screen.queryByRole("button", { name: "Copy answer" })).toBeNull();
  });
});
