import { fireEvent, render, screen, within } from "@testing-library/react";
import { ApiError } from "../api/client";
import type { Review } from "../api/reviews";
import { createFakeApi } from "../test/fakeAuth";
import Avatar, { colorFor, initials } from "./Avatar";
import PhotoLightbox from "./PhotoLightbox";
import PlaceGallery, { photosFromReviews } from "./PlaceGallery";
import ReviewList from "./ReviewList";
import ReviewSummaryCard from "./ReviewSummaryCard";

const photo = (n: number) => `https://lh3.googleusercontent.com/p${n}`;

function review(id: number, overrides: Partial<Review> = {}): Review {
  return {
    id,
    target_id: 1,
    source_review_id: `r-${id}`,
    source_platform: "google_maps",
    reviewer_name: `Reviewer ${id}`,
    rating: 4,
    text: `Review text ${id}`,
    review_date: null,
    created_at: "2026-11-10T00:00:00",
    reviewer_avatar_url: null,
    image_urls: [],
    ...overrides,
  };
}

describe("Avatar", () => {
  it("shows the profile picture", () => {
    render(<Avatar name="Ana Lee" src={photo(9)} />);

    expect(screen.getByTestId("avatar-image")).toHaveAttribute("src", photo(9));
  });

  it("falls back to initials when the picture fails or is missing", () => {
    const { rerender } = render(<Avatar name="Ana Lee" src={photo(9)} />);
    fireEvent.error(screen.getByTestId("avatar-image"));
    expect(screen.getByTestId("avatar-initials")).toHaveTextContent("AL");

    rerender(<Avatar name={null} />);
    expect(screen.getByTestId("avatar-initials")).toHaveTextContent("A");
  });

  it("builds stable initials and colors", () => {
    expect(initials("  joe's   pizza place ")).toBe("JP");
    expect(initials("   ")).toBe("?");
    expect(colorFor("Joe's Pizza")).toBe(colorFor("Joe's Pizza"));
  });
});

describe("PhotoLightbox", () => {
  const photos = [1, 2, 3].map((n) => ({
    url: photo(n),
    caption: `Photo ${n}`,
  }));

  it("moves with buttons and arrow keys and closes with Escape", () => {
    const onClose = vi.fn();
    const onNavigate = vi.fn();
    render(
      <PhotoLightbox
        photos={photos}
        index={0}
        onClose={onClose}
        onNavigate={onNavigate}
      />,
    );

    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Next photo" }));
    fireEvent.click(screen.getByRole("button", { name: "Previous photo" }));
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(onNavigate.mock.calls).toEqual([[1], [2], [1], [2]]);

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes when the backdrop is clicked but not the photo", () => {
    const onClose = vi.fn();
    render(
      <PhotoLightbox
        photos={photos.slice(0, 1)}
        index={0}
        onClose={onClose}
        onNavigate={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("img"));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Next photo" })).toBeNull();
  });

  it("renders nothing for an index outside the list", () => {
    const { container } = render(
      <PhotoLightbox
        photos={[]}
        index={0}
        onClose={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});

describe("PlaceGallery", () => {
  it("collects photos from reviews, capped at 24", () => {
    const reviews = [
      review(1, { image_urls: Array.from({ length: 20 }, (_, i) => photo(i)) }),
      review(2, {
        image_urls: Array.from({ length: 10 }, (_, i) => photo(50 + i)),
      }),
      review(3, { image_urls: undefined }),
    ];

    const photos = photosFromReviews(reviews);

    expect(photos).toHaveLength(24);
    expect(photos[0].caption).toBe("Reviewer 1, 4 out of 5");
  });

  it("shows customer photos and opens them full size", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue([
      review(1, { image_urls: [1, 2, 3, 4, 5, 6, 7].map(photo) }),
    ]);
    render(
      <PlaceGallery
        api={api}
        targetId="1"
        targetName="Joe's Pizza"
        refreshKey={0}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Photos from customers" }),
    ).toBeVisible();
    expect(
      screen.getByText("7 photos from reviews of Joe's Pizza"),
    ).toBeVisible();
    expect(screen.getByText("+2")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /Open photo 2 of 7/ }));
    const dialog = screen.getByRole("dialog", { name: "Photo 2 of 7" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Next photo" }));
    expect(screen.getByRole("dialog", { name: "Photo 3 of 7" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows a lettered tile when there are no photos or they can't load", async () => {
    const api = createFakeApi();
    api.request.mockRejectedValue(new ApiError(500, "unexpected", "nope"));
    render(
      <PlaceGallery
        api={api}
        targetId="1"
        targetName="Joe's Pizza"
        refreshKey={0}
      />,
    );

    expect(await screen.findByText("No customer photos yet")).toBeVisible();
    expect(screen.getByText("JP")).toBeInTheDocument();
  });
});

describe("ReviewList media", () => {
  it("shows avatars and opens a review's photos", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue([
      review(1, {
        reviewer_avatar_url: photo(99),
        image_urls: [1, 2, 3, 4, 5].map(photo),
      }),
    ]);
    render(<ReviewList api={api} targetId="1" refreshKey={0} />);

    expect(await screen.findByTestId("avatar-image")).toHaveAttribute(
      "src",
      photo(99),
    );
    expect(screen.getByText("+1")).toBeVisible();

    fireEvent.click(
      screen.getByRole("button", { name: "Open photo 2 of 5 from Reviewer 1" }),
    );
    expect(screen.getByRole("dialog", { name: "Photo 2 of 5" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Next photo" }));
    expect(screen.getByRole("dialog", { name: "Photo 3 of 5" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("ReviewSummaryCard review count", () => {
  const summary = {
    target_id: 1,
    target_name: "Joe's Pizza",
    review_count: 7,
    average_rating: 4.1,
    rating_distribution: { "1": 0, "2": 1, "3": 1, "4": 2, "5": 3 },
  };

  it("reports the loaded count", async () => {
    const api = createFakeApi();
    api.request.mockResolvedValue(summary);
    const onReviewCount = vi.fn();
    render(
      <ReviewSummaryCard
        api={api}
        targetId="1"
        targetName="Joe's Pizza"
        refreshKey={0}
        onReviewCount={onReviewCount}
      />,
    );

    await screen.findByTestId("summary-review-count");
    expect(onReviewCount).toHaveBeenLastCalledWith(7);
  });

  it.each([
    [
      "a failed request",
      () => Promise.reject(new ApiError(500, "unexpected", "x")),
    ],
    [
      "a summary for another target",
      () => Promise.resolve({ ...summary, target_id: 2 }),
    ],
  ])("reports an unknown count after %s", async (_label, respond) => {
    const api = createFakeApi();
    api.request.mockImplementation(respond);
    const onReviewCount = vi.fn();
    render(
      <ReviewSummaryCard
        api={api}
        targetId="1"
        targetName="Joe's Pizza"
        refreshKey={0}
        onReviewCount={onReviewCount}
      />,
    );

    await vi.waitFor(() => expect(onReviewCount).toHaveBeenCalledWith(null));
  });
});
