import { useEffect, useState } from "react";
import { Keyboard, X } from "lucide-react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { useHealth } from "./api/hooks";
import Styleguide from "./pages/Styleguide";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import ComparePage from "./pages/ComparePage";
import EvaluationPage from "./pages/EvaluationPage";
import FleetPage from "./pages/FleetPage";
import LiveLabPage from "./pages/LiveLabPage";

const Placeholder = ({ title }: { title: string }) => (
  <div className="mx-auto max-w-[1440px] px-6 py-8">
    <h1 className="heading text-xl">{title}</h1>
    <p className="mt-2 text-graphite">
      This page is built in its dedicated phase.
    </p>
  </div>
);
function Shell() {
  const health = useHealth();
  const navigate = useNavigate();
  const [shortcuts, setShortcuts] = useState(false);
  useEffect(() => {
    let prefix = false;
    const handler = (event: KeyboardEvent) => {
      if ((event.target as HTMLElement).matches("input, textarea, select"))
        return;
      if (event.key === "?") setShortcuts(true);
      if (event.key === "g") {
        prefix = true;
        return;
      }
      if (prefix) {
        const routes: Record<string, string> = {
          r: "/",
          e: "/eval",
          f: "/fleet",
          l: "/lab",
        };
        if (routes[event.key]) navigate(routes[event.key]);
        prefix = false;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate]);
  const links = [
    ["/", "Runs"],
    ["/eval", "Evaluation"],
    ["/fleet", "Fleet"],
    ["/lab", "Live lab"],
  ];
  return (
    <>
      <header className="sticky top-0 z-40 h-14 border-b border-rule bg-panel">
        <div className="mx-auto flex h-full max-w-[1440px] items-center gap-8 px-6">
          <NavLink to="/" className="flex items-center gap-2">
            <span className="h-3.5 w-3.5 bg-orange" />
            <span className="heading text-[18px]">Black Box</span>
          </NavLink>
          <nav className="flex h-full items-center gap-6">
            {links.map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex h-full items-center border-b-2 pt-0.5 text-sm ${isActive ? "border-ink text-ink" : "border-transparent text-graphite"}`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <span className="rounded-chip bg-rule-soft px-2.5 py-1 text-xs">
              {import.meta.env.VITE_USE_MOCKS === "true"
                ? "Demo data"
                : health.data?.demo_mode
                  ? "Demo mode"
                  : "Live"}
            </span>
            <span className="font-mono text-xs text-graphite">
              {health.data?.model_version ?? "v3"}
            </span>
            <button
              aria-label="Keyboard shortcuts"
              onClick={() => setShortcuts(true)}
            >
              <Keyboard className="h-4 w-4 text-graphite" />
            </button>
          </div>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<RunsPage />} />
          <Route path="/runs/:id" element={<RunDetailPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/eval" element={<EvaluationPage />} />
          <Route path="/fleet" element={<FleetPage />} />
          <Route path="/lab" element={<LiveLabPage />} />
          <Route path="/styleguide" element={<Styleguide />} />
        </Routes>
      </main>
      {shortcuts && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-ink/20"
          onClick={() => setShortcuts(false)}
        >
          <div
            role="dialog"
            aria-label="Keyboard shortcuts"
            className="w-80 rounded-panel border border-rule bg-panel p-5 shadow-popover"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex justify-between">
              <h2 className="heading text-lg">Keyboard shortcuts</h2>
              <button aria-label="Close" onClick={() => setShortcuts(false)}>
                <X />
              </button>
            </div>
            <dl className="mt-4 grid grid-cols-[70px_1fr] gap-2 text-sm">
              <dt className="font-mono">g r</dt>
              <dd>Runs</dd>
              <dt className="font-mono">g e</dt>
              <dd>Evaluation</dd>
              <dt className="font-mono">g f</dt>
              <dd>Fleet</dd>
              <dt className="font-mono">g l</dt>
              <dd>Live lab</dd>
              <dt className="font-mono">?</dt>
              <dd>This sheet</dd>
            </dl>
          </div>
        </div>
      )}
    </>
  );
}
function App() {
  return <Shell />;
}

export default App;
