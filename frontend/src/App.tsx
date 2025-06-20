import { Toaster } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { TooltipProvider } from "@/components/ui/tooltip";

// Import components
import Header from "./components/Header";
import TermSelector from "./components/TermSelector";
import CourseSelector from "./components/CourseSelector";
import CourseDetailsDisplay from "./components/CourseDetailsDisplay";
import Footer from "./components/Footer";
import { CourseSelectionProvider } from "@/contexts/CourseSelectionContext";

/**
 * === App Component ===
 * Main application shell. Wraps content with context providers.
 */
function App() {
  // Selection state is now managed by CourseSelectionProvider

  return (
    <TooltipProvider>
      <CourseSelectionProvider>
        <div className="container mx-auto p-4 md:p-8 lg:p-12 min-h-[100dvh] flex flex-col">
          <Toaster richColors position="top-right" theme="system" closeButton />
          <Header />
          <Separator />

          <main className="flex-grow">

            <Card className="my-6">
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

          </main>

          <Footer />
        </div>
      </CourseSelectionProvider>
    </TooltipProvider>
  );
}

export default App;