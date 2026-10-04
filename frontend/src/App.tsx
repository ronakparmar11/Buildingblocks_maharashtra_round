import { useEffect, useState } from "react";
import { ChevronDown, Keyboard, LogOut, Menu, X } from "lucide-react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { apiGet, apiPost } from "./api/client";
import type { SessionResponse } from "./api/types";
import { LogoMark } from "./components/Logo";
import { Popover } from "./components/ui";
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
import IncidentsPage from "./pages/IncidentsPage";
import IncidentDetailPage from "./pages/IncidentDetailPage";
import SettingsNotificationsPage from "./pages/SettingsNotificationsPage";
import LandingPage from "./pages/LandingPage";
import SignInPage from "./pages/SignInPage";
import VoiceLabPage from "./pages/VoiceLabPage";

function LegacyRunRedirect() {
  const { id } = useParams();
  const location = useLocation();
  return <Navigate replace to={`${id ? `/conversations/${id}` : "/conversations"}${location.search}`} />;
}

// function useTheme() {
//   const [dark, setDark] = useState(() => {
//     const stored = localStorage.getItem("blackbox-theme");
//     if (stored) return stored === "dark";
//     return window.matchMedia("(prefers-color-scheme: dark)").matches;
//   });
//   useEffect(() => {
//     document.documentElement.classList.toggle("dark", dark);
//     localStorage.setItem("blackbox-theme", dark ? "dark" : "light");
//   }, [dark]);
//   return { dark, toggle: () => setDark((d) => !d) };
// }

function Shell({ session, onSignedOut }: { session: SessionResponse; onSignedOut: () => void }) {
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
          v: "/voice-lab",
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
    ["/voice-lab", "Voice lab"],
    ["/settings", "Settings"],
  ];
  return (
    <>
      <header className="sticky top-0 z-40 h-14 border-b border-rule bg-panel">
        <div className="mx-auto flex h-full max-w-[1440px] items-center gap-3 px-3 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2">
            <LogoMark className="h-7 w-7" />
            <span className="heading hidden text-[18px] sm:inline">
              Black Box
            </span>
          </NavLink>
          <Popover
            closeOnContentClick
            trigger={
              <button className="flex h-9 max-w-[calc(100vw-9.5rem)] items-center gap-2 rounded-control border border-rule bg-panel px-3 text-left text-sm sm:max-w-[220px]">
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
          <nav className="hidden h-full min-w-0 items-center gap-5 md:flex">
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
            <span className="md:hidden">
              <Popover
                closeOnContentClick
                trigger={
                  <button
                    aria-label="Open navigation"
                    className="grid h-9 w-9 place-items-center rounded-control border border-rule bg-panel"
                  >
                    <Menu className="h-4 w-4" />
                  </button>
                }
              >
                <nav className="grid min-w-48 gap-1">
                  {links.map(([to, label]) => (
                    <NavLink
                      key={to}
                      to={to}
                      end={to === "/"}
                      className={({ isActive }) =>
                        `rounded-control px-3 py-2 text-sm font-medium ${isActive ? "bg-rule-soft text-ink" : "text-graphite hover:bg-rule-soft/60"}`
                      }
                    >
                      {label}
                    </NavLink>
                  ))}
                </nav>
              </Popover>
            </span>
            <button
              aria-label="Keyboard shortcuts"
              onClick={() => setShortcuts(true)}
              className="hidden rounded-control transition-colors hover:bg-rule-soft focus-visible:ring-2 focus-visible:ring-advisory sm:block"
            >
              <Keyboard className="h-4 w-4 text-graphite" />
            </button>
            <button title={`Sign out ${session.email}`} aria-label="Sign out" onClick={onSignedOut} className="grid h-8 w-8 place-items-center rounded-control text-graphite transition-colors hover:bg-rule-soft focus-visible:ring-2 focus-visible:ring-advisory"><LogOut className="h-4 w-4" /></button>
          </div>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/signin" element={<Navigate replace to="/" />} />
          <Route path="/" element={<OverviewPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/incidents/:id" element={<IncidentDetailPage />} />
          <Route path="/conversations" element={<RunsPage />} />
          <Route path="/conversations/:id" element={<RunDetailPage />} />
          <Route path="/runs" element={<LegacyRunRedirect />} />
          <Route path="/runs/:id" element={<LegacyRunRedirect />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/eval" element={<EvaluationPage />} />
          <Route path="/fleet" element={<Navigate replace to="/" />} />
          <Route path="/lab" element={<LiveLabPage />} />
          <Route path="/voice-lab" element={<VoiceLabPage />} />
          <Route path="/settings" element={<Navigate replace to="/settings/notifications" />} />
          <Route path="/settings/notifications" element={<SettingsNotificationsPage />} />
          <Route path="/styleguide" element={<Styleguide />} />
        </Routes>
      </main>
      {shortcuts && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/20 animate-[fadeIn_150ms_ease-out]"
          onClick={() => setShortcuts(false)}
        >
          <div
            role="dialog"
            aria-label="Keyboard shortcuts"
            className="w-80 rounded-panel border border-rule bg-panel p-5 shadow-popover animate-[scaleIn_150ms_ease-out]"
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
              <dt className="font-mono">g v</dt>
              <dd>Voice lab</dd>
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
  const [session, setSession] = useState<SessionResponse | null | undefined>();
  useEffect(() => {
    apiGet<SessionResponse>("/auth/session").then(setSession).catch(() => setSession(null));
  }, []);
  if (session === undefined) return <div className="grid min-h-screen place-items-center bg-[#14202B] text-sm text-white/70"><div className="flex flex-col items-center gap-4"><LogoMark className="h-12 w-12 animate-pulse" /><span>Opening Black Box...</span></div></div>;
  if (session === null) return <Routes><Route path="/" element={<LandingPage />} /><Route path="/signin" element={<SignInPage onSignedIn={setSession} />} /><Route path="*" element={<Navigate replace to="/" />} /></Routes>;
  const signOut = async () => {
    await apiPost<void>("/auth/logout");
    setSession(null);
  };
  return <Shell session={session} onSignedOut={signOut} />;
}

export default App;
