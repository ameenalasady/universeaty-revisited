import { useState, useEffect } from "react";
import { Toaster } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { TooltipProvider } from "@/components/ui/tooltip";

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
        <div className="container mx-auto p-4 md:p-8 lg:p-12 min-h-[100dvh] flex flex-col">
          <Toaster richColors position="top-right" theme="system" closeButton />
          <Header currentView={view} onViewChange={setView} />
          <Separator className="mb-2" />

          <main className="flex-grow">
            {view === "home" ? (
              <>
                <Card className="my-6 border-border/40 bg-card/30 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle>Course Selection</CardTitle>
                    <CardDescription>
                      Choose a term and then select the course you're interested in.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
                    <TermSelector />
                    <CourseSelector />
                  </CardContent>
                </Card>

                <CourseDetailsDisplay />
              </>
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
