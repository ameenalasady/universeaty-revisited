import React from "react";
import { Button } from "@/components/ui/button";
import { Heart, X } from "lucide-react";

interface DonationBannerProps {
  onDismiss: () => void;
}

/**
 * Shared "Support Universeaty" banner.
 * Rendered as a centered stack on mobile and a row on large screens.
 */
const DonationBanner: React.FC<DonationBannerProps> = ({ onDismiss }) => {
  return (
    <div className="relative flex flex-col items-center justify-between gap-5 overflow-hidden rounded-xl border border-primary/20 bg-primary/5 p-4 pr-10 animate-in fade-in slide-in-from-top-4 duration-500 sm:p-5 sm:pr-12 lg:flex-row lg:pr-12">
      <div className="absolute top-2 right-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-full text-muted-foreground hover:bg-primary/10"
          onClick={onDismiss}
          aria-label="Dismiss support banner"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div className="z-10 flex w-full flex-col items-center gap-4 text-center sm:flex-row sm:text-left">
        <div className="flex shrink-0 rounded-full bg-primary/10 p-3 text-primary">
          <Heart className="h-6 w-6" />
        </div>
        <div className="flex-1 sm:pr-6">
          <p className="mb-1 text-base font-bold leading-tight text-foreground">
            Support Universeaty
          </p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            This project is run out-of-pocket and has processed over 20,000 watch requests. If it
            helped you get a seat, please consider supporting the development.
          </p>
        </div>
      </div>
      <Button
        variant="default"
        size="lg"
        className="z-10 h-11 w-full shrink-0 font-semibold whitespace-nowrap shadow-md lg:h-10 lg:w-auto"
        onClick={() => window.open("https://ko-fi.com/ameenalasady", "_blank")}
      >
        <Heart className="mr-2 h-4 w-4" />
        Support on Ko-fi
      </Button>
    </div>
  );
};

export default DonationBanner;
