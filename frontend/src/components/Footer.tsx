import React from "react";
import { Coffee, Github, Signal } from "lucide-react";

const links = [
  {
    href: "https://ko-fi.com/ameenalasady",
    label: "Support on Ko-fi",
    icon: Coffee,
  },
  {
    href: "https://github.com/ameenalasady/universeaty-revisited",
    label: "View on GitHub",
    icon: Github,
  },
  {
    href: "https://stats.uptimerobot.com/CmsUh6hffi",
    label: "Service Status",
    icon: Signal,
  },
];

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto border-t border-border/40 py-6">
      <nav className="flex flex-wrap items-center justify-center gap-x-1 gap-y-1 sm:gap-x-2">
        {links.map(({ href, label, icon: Icon }) => (
          <a
            key={href}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground sm:text-sm"
          >
            <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            {label}
          </a>
        ))}
      </nav>
      <p className="mt-3 text-center text-[11px] text-muted-foreground/60">
        Free &amp; open-source course seat monitoring for McMaster University
      </p>
    </footer>
  );
};

export default Footer;
