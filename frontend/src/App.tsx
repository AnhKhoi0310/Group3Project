import { Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav
          aria-label="Main"
          className="mx-auto flex h-14 max-w-6xl items-center px-6"
        >
          <span className="text-lg font-semibold">ReviewLens AI</span>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route
            path="/"
            element={<h1 className="text-2xl font-semibold">Welcome</h1>}
          />
        </Routes>
      </main>
    </div>
  );
}
