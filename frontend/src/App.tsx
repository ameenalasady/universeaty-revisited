import { useState, useEffect } from "react";
import { Toaster } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipProvider } from "@/components/ui/tooltip";
import { GraduationCap } from "lucide-react";

// Import components
import Header from "./components/Header";
import TermSelector from "./components/TermSelector";
import CourseSelector from "./components/CourseSelector";
import CourseDetailsDisplay from "./components/CourseDetailsDisplay";
import Footer from "./components/Footer";
import ManageWatches from "./pages/ManageWatches";
import { CourseSelectionProvider } from "@/contexts/CourseSelectionContext";

/**
 * === App Component ===
 * Main application shell. Wraps content with context providers.
 */
function App() {
  const [view, setView] = useState<"home" | "manage">(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("token") || urlParams.get("view") === "manage") {
      return "manage";
    }
    return "home";
  });

  // Sync URL with view state
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (view === "manage") {
      if (urlParams.get("view") !== "manage") {
        urlParams.set("view", "manage");
        window.history.replaceState({}, "", `${window.location.pathname}?${urlParams.toString()}`);
      }
    } else {
      if (urlParams.has("view")) {
        urlParams.delete("view");
        const search = urlParams.toString();
        const newUrl = window.location.pathname + (search ? `?${search}` : "");
        window.history.replaceState({}, "", newUrl);
      }
    }
  }, [view]);

  return (
    <TooltipProvider>
      <CourseSelectionProvider>
        <div className="mx-auto flex min-h-[100dvh] w-full max-w-5xl flex-col px-4 sm:px-6 lg:px-8">
          <Toaster richColors position="top-right" theme="system" closeButton />
          <Header currentView={view} onViewChange={setView} />

          <main className="flex-grow py-6 sm:py-8">
            {view === "home" ? (
              <div className="space-y-6">
                <Card className="border-border/50 bg-card/40 shadow-sm backdrop-blur-sm">
                  <CardHeader>
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                        <GraduationCap className="h-4 w-4" />
                      </span>
                      <div className="flex flex-col gap-1">
                        <CardTitle className="text-lg">Course Selection</CardTitle>
                        <CardDescription>
                          Choose a term, then pick the course you're interested in.
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5">
                    <TermSelector />
                    <CourseSelector />
                  </CardContent>
                </Card>

                <CourseDetailsDisplay />
              </div>
            ) : (
              <ManageWatches />
            )}
          </main>

          <Footer />
        </div>
      </CourseSelectionProvider>
    </TooltipProvider>
  );
}

export default App;
