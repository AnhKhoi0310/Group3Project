import { fireEvent, render, screen } from "@testing-library/react";
import { ApiError } from "../api/client";
import type { Review } from "../api/reviews";
import { createFakeApi } from "../test/fakeAuth";
import ReviewList from "./ReviewList";

function review(id: number, overrides: Partial<Review> = {}): Review {
  return {
    id,
    target_id: 1,
    source_review_id: `r-${id}`,
    source_platform: "google_maps",
    reviewer_name: `Reviewer ${id}`,
    rating: 4,
    text: `Review text ${id}`,
    review_date: "3 months ago",
    created_at: "2026-11-10T00:00:00",
    ...overrides,
  };
}

function renderList(api = createFakeApi(), refreshKey = 0) {
  const view = render(
    <ReviewList api={api} targetId="1" refreshKey={refreshKey} />,
  );
  return { api, view };
}

describe("ReviewList", () => {
  it("loads saved reviews for this target with text, rating and metadata", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue([
      review(1, { rating: 5, text: "Best pizza in town" }),
      review(2, { rating: 2, reviewer_name: null, review_date: null }),
    ]);
    renderList(api);

    expect(await screen.findByText("Best pizza in town")).toBeVisible();
    expect(api.request).toHaveBeenCalledWith("/api/targets/1/reviews");
    expect(
      screen.getByRole("heading", { name: "Saved reviews (2)" }),
    ).toBeVisible();
    expect(screen.getByRole("img", { name: "5 out of 5 stars" })).toBeVisible();
    expect(screen.getByRole("img", { name: "2 out of 5 stars" })).toBeVisible();
    expect(screen.getByText("Reviewer 1")).toBeVisible();
    expect(screen.getByText("3 months ago")).toBeVisible();
    expect(screen.getByText("Anonymous")).toBeVisible();
  });

  it("shows the first ten and reveals the rest on request", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(
      Array.from({ length: 12 }, (_, i) => review(i + 1)),
    );
    renderList(api);

    expect(await screen.findByText("Review text 10")).toBeVisible();
    expect(screen.queryByText("Review text 11")).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Show all 12 reviews" }),
    );

    expect(screen.getByText("Review text 12")).toBeVisible();
  });

  it("explains what to do when nothing has been collected", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue([]);
    renderList(api);

    expect(await screen.findByText(/No reviews saved yet/)).toBeVisible();
  });

  it("shows a friendly error and no reviews when access is denied", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(
      new ApiError(404, "target_not_found", "We couldn't find that target."),
    );
    renderList(api);

    expect(
      await screen.findByText("We couldn't find that target."),
    ).toBeVisible();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("never shows raw error text from an unexpected failure", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(new Error("SQL exploded: secret-sql"));
    renderList(api);

    expect(
      await screen.findByText(
        "We couldn't load the saved reviews. Please try again.",
      ),
    ).toBeVisible();
    expect(screen.queryByText(/secret-sql/)).not.toBeInTheDocument();
  });

  it("reloads from the backend when asked to refresh", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValueOnce([]).mockResolvedValueOnce([review(1)]);
    const { view } = renderList(api);
    await screen.findByText(/No reviews saved yet/);

    view.rerender(<ReviewList api={api} targetId="1" refreshKey={1} />);

    expect(await screen.findByText("Review text 1")).toBeVisible();
    expect(api.request).toHaveBeenCalledTimes(2);
  });
});
