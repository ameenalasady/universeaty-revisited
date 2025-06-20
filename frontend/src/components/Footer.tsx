import React from "react";
import { Button } from "@/components/ui/button";
import { Coffee, Github, Signal } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="mt-6 py-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted-foreground border-t">
      {/* Ko-fi Link */}
      <Button
        variant="link"
        asChild
        className="text-muted-foreground p-0 h-auto"
      >
        <a
          href="https://ko-fi.com/ameenalasady"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Coffee className="mr-1.5 h-4 w-4" />
          Support on Ko-fi
        </a>
      </Button>
      {/* GitHub Link */}
      <Button
        variant="link"
        asChild
        className="text-muted-foreground p-0 h-auto"
      >
        <a
          href="https://github.com/ameenalasady/universeaty-revisited"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Github className="mr-1.5 h-4 w-4" />
          View on GitHub
        </a>
      </Button>
      {/* Status Page Link */}
      <Button
        variant="link"
        asChild
        className="text-muted-foreground p-0 h-auto"
      >
        <a
          href="https://stats.uptimerobot.com/CmsUh6hffi"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Signal className="mr-1.5 h-4 w-4" />
          Service Status
        </a>
      </Button>
    </footer>
  );
};

export default Footer;