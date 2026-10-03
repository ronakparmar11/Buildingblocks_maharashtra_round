import { useEffect, useState } from "react";
import { ChevronDown, Keyboard, X } from "lucide-react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useHealth } from "./api/hooks";
import { EmptyState, Popover } from "./components/ui";
import {
  useWorkspace,
  workspaceDetails,
  type WorkspaceId,
} from "./context/workspace";
import Styleguide from "./pages/Styleguide";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import ComparePage from "./pages/ComparePage";
import EvaluationPage from "./pages/EvaluationPage";
import LiveLabPage from "./pages/LiveLabPage";
import OverviewPage from "./pages/OverviewPage";

function LegacyRunRedirect() {
  const { id } = useParams();
  const location = useLocation();
  return <Navigate replace to={`${id ? `/conversations/${id}` : "/conversations"}${location.search}`} />;
}

const Placeholder = ({ title, empty }: { title: string; empty: string }) => (
  <div className="mx-auto max-w-[1200px] px-6 py-8">
    <h1 className="heading text-xl">{title}</h1>
    <EmptyState title={empty} />
  </div>
);

function Shell() {
  const health = useHealth();
  const { workspace, setWorkspace } = useWorkspace();
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
          o: "/",
          i: "/incidents",
          c: "/conversations",
          e: "/eval",
          l: "/lab",
          s: "/settings",
        };
        if (routes[event.key]) navigate(routes[event.key]);
        prefix = false;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate]);
  const links = [
    ["/", "Overview"],
    ["/incidents", "Incidents"],
    ["/conversations", "Conversations"],
    ["/eval", "Evaluation"],
    ["/lab", "Live lab"],
    ["/settings", "Settings"],
  ];
  return (
    <>
      <header className="sticky top-0 z-40 h-14 border-b border-rule bg-panel">
        <div className="mx-auto flex h-full max-w-[1440px] items-center gap-3 px-3 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2">
            <span className="h-3.5 w-3.5 bg-orange" />
            <span className="heading hidden text-[18px] sm:inline">
              Black Box
            </span>
          </NavLink>
          <Popover
            closeOnContentClick
            trigger={
              <button className="flex h-9 max-w-[220px] items-center gap-2 rounded-control border border-rule bg-panel px-3 text-left text-sm">
                <span className="truncate font-medium">{workspaceDetails[workspace].name}</span>
                <ChevronDown className="h-4 w-4 shrink-0 text-graphite" />
              </button>
            }
          >
            <span className="block space-y-1">
              {(Object.entries(workspaceDetails) as [WorkspaceId, (typeof workspaceDetails)[WorkspaceId]][]).map(([id, item]) => (
                <button
                  key={id}
                  onClick={() => setWorkspace(id)}
                  className={`block w-full rounded-control px-3 py-2 text-left ${workspace === id ? "bg-rule-soft" : "hover:bg-rule-soft/60"}`}
                >
                  <strong className="block text-sm">{item.name}</strong>
                  <span className="mt-0.5 block text-xs text-graphite">{item.description}</span>
                </button>
              ))}
            </span>
          </Popover>
          <nav className="flex h-full min-w-0 items-center gap-3 overflow-x-auto sm:gap-5">
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
          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <span className="rounded-chip bg-rule-soft px-2.5 py-1 text-xs">
              {import.meta.env.VITE_USE_MOCKS === "true"
                ? "Demo data"
                : health.data?.demo_mode
                  ? "Demo mode"
                  : "Live"}
            </span>
            <span className="hidden font-mono text-xs text-graphite md:inline">
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
          <Route path="/" element={<OverviewPage />} />
          <Route path="/incidents" element={<Placeholder title="Incidents" empty="No open incidents. Wrong answers will be grouped here as they happen." />} />
          <Route path="/conversations" element={<RunsPage />} />
          <Route path="/conversations/:id" element={<RunDetailPage />} />
          <Route path="/runs" element={<LegacyRunRedirect />} />
          <Route path="/runs/:id" element={<LegacyRunRedirect />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/eval" element={<EvaluationPage />} />
          <Route path="/fleet" element={<Navigate replace to="/" />} />
          <Route path="/lab" element={<LiveLabPage />} />
          <Route path="/settings" element={<Placeholder title="Settings" empty="No notification settings are available for this workspace." />} />
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
              <dt className="font-mono">g o</dt>
              <dd>Overview</dd>
              <dt className="font-mono">g i</dt>
              <dd>Incidents</dd>
              <dt className="font-mono">g c</dt>
              <dd>Conversations</dd>
              <dt className="font-mono">g e</dt>
              <dd>Evaluation</dd>
              <dt className="font-mono">g l</dt>
              <dd>Live lab</dd>
              <dt className="font-mono">g s</dt>
              <dd>Settings</dd>
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
