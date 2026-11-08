import { render, screen } from "@testing-library/react";
import Root from "./Root";

const VALID_ENV = {
  VITE_API_BASE_URL: "http://localhost:8000",
  VITE_FIREBASE_API_KEY: "web-key",
  VITE_FIREBASE_AUTH_DOMAIN: "demo.firebaseapp.com",
  VITE_FIREBASE_PROJECT_ID: "demo",
  VITE_FIREBASE_APP_ID: "app-id",
};

describe("Root", () => {
  it("renders the application when configuration is valid", () => {
    render(<Root env={VALID_ENV} />);

    expect(screen.getByRole("navigation", { name: "Main" })).toHaveTextContent(
      "ReviewLens AI",
    );
  });

  it("explains which configuration is missing instead of rendering the app", () => {
    render(<Root env={{ ...VALID_ENV, VITE_FIREBASE_APP_ID: "" }} />);

    expect(screen.getByRole("alert")).toHaveTextContent("VITE_FIREBASE_APP_ID");
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });
});
