// Sprint 2 extra: review explorer (tag: Reviews) and chat dock (tag: Chat dock).
// Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import type { Review } from "../api/reviews";
import { createFakeApi } from "../test/fakeAuth";
import ChatDock, { DEFAULT_WIDTH, MAX_WIDTH, MIN_WIDTH } from "./ChatDock";
import ReviewList, { focusReview, Highlight } from "./ReviewList";

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

const REVIEWS = [
  review(1, { rating: 5, text: "Crispy crust and great sauce." }),
  review(2, { rating: 2, text: "Long wait, cold slice." }),
  review(3, {
    rating: 4,
    text: "Good crust, cash only.",
    image_urls: [
      "https://lh3.googleusercontent.com/a",
      "https://lh3.googleusercontent.com/b",
    ],
  }),
  review(4, {
    rating: 1,
    text: "Rude at the counter.",
    reviewer_name: "Crusty Joe",
  }),
];

async function renderExplorer() {
  const api = createFakeApi();
  api.request.mockResolvedValue(REVIEWS);
  render(<ReviewList api={api} targetId="1" refreshKey={0} />);
  await screen.findByText("Showing 4 of 4 reviews");
  return api;
}

const listedTexts = () =>
  within(screen.getByTestId("review-scroll"))
    .getAllByRole("listitem")
    .filter((item) => item.querySelector("p"))
    .map((item) => item.querySelector("p.whitespace-pre-line")?.textContent);

describe("Review explorer", () => {
  // Reviews: search finds text and reviewer names and highlights matches
  it("searches text and reviewer names and highlights the matches", async () => {
    await renderExplorer();

    fireEvent.change(screen.getByLabelText("Search reviews"), {
      target: { value: "crust" },
    });

    expect(screen.getByText("Showing 3 of 4 reviews")).toBeVisible();
    expect(listedTexts()).toEqual([
      "Crispy crust and great sauce.",
      "Good crust, cash only.",
      "Rude at the counter.",
    ]);
    const marks = document.querySelectorAll("mark");
    expect([...marks].map((mark) => mark.textContent)).toEqual([
      "crust",
      "crust",
      "Crust",
    ]);
  });

  // Reviews: star filters narrow the list and toggle off
  it("filters by star rating and toggles the filter off", async () => {
    await renderExplorer();
    const fiveStar = screen.getByRole("button", { name: "5-star reviews (1)" });

    fireEvent.click(fiveStar);
    expect(fiveStar).toHaveAttribute("aria-pressed", "true");
    expect(listedTexts()).toEqual(["Crispy crust and great sauce."]);

    fireEvent.click(fiveStar);
    expect(screen.getByText("Showing 4 of 4 reviews")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "3-star reviews (0)" }),
    ).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "2-star reviews (1)" }));
    fireEvent.click(screen.getByRole("button", { name: "All (4)" }));
    expect(screen.getByText("Showing 4 of 4 reviews")).toBeVisible();
  });

  // Reviews: sort by rating or photos
  it("sorts by rating and by photos", async () => {
    await renderExplorer();
    const sort = screen.getByLabelText("Sort by");

    fireEvent.change(sort, { target: { value: "lowest" } });
    expect(listedTexts()[0]).toBe("Rude at the counter.");

    fireEvent.change(sort, { target: { value: "highest" } });
    expect(listedTexts()[0]).toBe("Crispy crust and great sauce.");

    fireEvent.change(sort, { target: { value: "photos" } });
    expect(listedTexts()[0]).toBe("Good crust, cash only.");

    fireEvent.change(sort, { target: { value: "newest" } });
    expect(listedTexts()[0]).toBe("Crispy crust and great sauce.");
  });

  // Reviews: no matches explains and clears the filters
  it("explains when nothing matches and clears the filters", async () => {
    await renderExplorer();
    fireEvent.click(screen.getByRole("button", { name: "2-star reviews (1)" }));
    fireEvent.change(screen.getByLabelText("Search reviews"), {
      target: { value: "pineapple" },
    });

    expect(
      screen.getByText('No reviews match "pineapple" with 2 stars.'),
    ).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    expect(screen.getByText("Showing 4 of 4 reviews")).toBeVisible();
    expect(screen.getByLabelText("Search reviews")).toHaveValue("");
  });

  // Reviews: Show in reviews jumps to a review and clears hiding filters
  it("jumps to a review from the chat, clearing filters that hide it", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    try {
      await renderExplorer();
      fireEvent.click(
        screen.getByRole("button", { name: "5-star reviews (1)" }),
      );

      act(() => focusReview(4));

      const focused = document.querySelector("[data-focused]");
      expect(focused).toHaveTextContent("Rude at the counter.");
      expect(scrollIntoView).toHaveBeenCalled();
      expect(screen.getByText("Showing 4 of 4 reviews")).toBeVisible();

      act(() => vi.advanceTimersByTime(3000));
      expect(document.querySelector("[data-focused]")).toBeNull();
    } finally {
      vi.useRealTimers();
      // @ts-expect-error restore the jsdom default (no scrollIntoView)
      delete Element.prototype.scrollIntoView;
    }
  });

  // Reviews: search terms with symbols match literally
  it("highlights special characters literally", () => {
    render(
      <p>
        <Highlight text="Price (cash) only" query="(cash)" />
      </p>,
    );

    expect(document.querySelector("mark")).toHaveTextContent("(cash)");
  });
});

describe("ChatDock", () => {
  // jsdom has no PointerEvent, so pointer coordinates would be lost.
  beforeAll(() => {
    if (!window.PointerEvent) {
      class TestPointerEvent extends MouseEvent {
        pointerId: number;
        constructor(type: string, init: PointerEventInit = {}) {
          super(type, init);
          this.pointerId = init.pointerId ?? 0;
        }
      }
      window.PointerEvent = TestPointerEvent as unknown as typeof PointerEvent;
    }
  });

  function renderDock(props: Partial<Parameters<typeof ChatDock>[0]> = {}) {
    const onResize = vi.fn();
    const onClose = vi.fn();
    render(
      <ChatDock
        open
        width={DEFAULT_WIDTH}
        label="Chat"
        onClose={onClose}
        onResize={onResize}
        {...props}
      >
        <p>Chat body</p>
      </ChatDock>,
    );
    return { onResize, onClose };
  }

  // Chat dock: arrow keys resize within limits
  it("resizes with the keyboard, clamped to its limits", () => {
    const { onResize } = renderDock();
    const handle = screen.getByRole("separator", { name: "Resize chat" });

    fireEvent.keyDown(handle, { key: "ArrowLeft" });
    fireEvent.keyDown(handle, { key: "ArrowRight" });
    fireEvent.keyDown(handle, { key: "Home" });
    fireEvent.keyDown(handle, { key: "End" });
    fireEvent.keyDown(handle, { key: "a" });
    fireEvent.doubleClick(handle);

    expect(onResize.mock.calls).toEqual([
      [DEFAULT_WIDTH + 24],
      [DEFAULT_WIDTH - 24],
      [MAX_WIDTH],
      [MIN_WIDTH],
      [DEFAULT_WIDTH],
    ]);
  });

  // Chat dock: dragging the edge resizes
  it("resizes by dragging the left edge", () => {
    const { onResize } = renderDock();
    const handle = screen.getByRole("separator", { name: "Resize chat" });

    fireEvent.pointerMove(handle, { clientX: 500 }); // ignored before a press
    fireEvent.pointerDown(handle, { clientX: 1000, pointerId: 1 });
    fireEvent.pointerMove(handle, { clientX: 900 });
    fireEvent.pointerMove(handle, { clientX: 100 });
    fireEvent.pointerUp(handle);
    fireEvent.pointerMove(handle, { clientX: 0 });

    expect(onResize.mock.calls).toEqual([[DEFAULT_WIDTH + 100], [MAX_WIDTH]]);
  });

  // Chat dock: a closed chat is hidden from screen readers
  it("hides its content from assistive technology when closed", () => {
    renderDock({ open: false });

    const dock = screen.getByTestId("chat-dock");
    expect(dock).toHaveAttribute("aria-hidden", "true");
    expect(dock).toHaveAttribute("data-open", "false");
  });

  // Chat dock: clicking the backdrop closes it
  it("closes when the backdrop is clicked", () => {
    const { onClose } = renderDock();

    fireEvent.click(document.querySelector("div[aria-hidden='true']")!);

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
