import React, { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { requestAuthCode, verifyAuthCode, logoutUser, getAuthStatus } from "../services/api";
import WatchDashboard from "../components/WatchDashboard";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/card";
import { toast } from "sonner";
import { Loader2, LogOut, Eye } from "lucide-react";

export const ManageWatches: React.FC = () => {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [step, setStep] = useState<"email" | "code" | "authenticated">("email");
  const [checkingAuth, setCheckingAuth] = useState(true);
  const queryClient = useQueryClient();

  // Check for magic link token or existing session on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get("token");
    const urlEmail = urlParams.get("email");

    if (urlToken) {
      // Sanitize magic link token: trim whitespace and normalize to uppercase
      setToken(sanitizeToken(urlToken));
      if (urlEmail) setEmail(urlEmail.trim().toLowerCase());
      setStep("code");
      setCheckingAuth(false);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname + "?view=manage");
    } else {
      // Check if already logged in
      getAuthStatus()
        .then((data) => {
          setEmail(data.email);
          setStep("authenticated");
        })
        .catch(() => {
          // Not logged in, stay on email step
        })
        .finally(() => {
          setCheckingAuth(false);
        });
    }
  }, []);

  const requestMutation = useMutation({
    mutationFn: requestAuthCode,
    onSuccess: () => {
      toast.success("Verification code sent to your email!");
      setStep("code");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to send code");
    },
  });

  const verifyMutation = useMutation({
    mutationFn: verifyAuthCode,
    onSuccess: () => {
      toast.success("Successfully authenticated!");
      setStep("authenticated");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Invalid or expired code");
    },
  });

  const logoutMutation = useMutation({
    mutationFn: logoutUser,
    onSuccess: () => {
      toast.success("Logged out");
      setStep("email");
      setEmail("");
      setToken("");
      queryClient.clear();
    },
  });

  // Auto-submit when a full 7-character token is entered
  useEffect(() => {
    if (token.length === 7 && step === "code" && email && !verifyMutation.isPending) {
      verifyMutation.mutate({ email: email.trim().toLowerCase(), token });
    }
  }, [token, step, email, verifyMutation]);

  /** Sanitizes a raw token string: trims whitespace, uppercases, and formats as XXX-XXX */
  const sanitizeToken = (raw: string): string => {
    // Strip all whitespace, uppercase
    const clean = raw.replace(/\s/g, "").toUpperCase();
    // Auto-insert dash if not present and length >= 3
    if (clean.length > 3 && !clean.includes("-")) {
      return `${clean.slice(0, 3)}-${clean.slice(3, 6)}`;
    }
    // Remove any extra characters beyond the 7-char XXX-XXX format
    return clean.slice(0, 7);
  };

  const handleTokenChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const sanitized = sanitizeToken(e.target.value);
    setToken(sanitized);
  };

  const handleRequestCode = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail) return;
    setEmail(trimmedEmail);
    requestMutation.mutate({ email: trimmedEmail });
  };

  const handleVerifyCode = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedEmail = email.trim().toLowerCase();
    const trimmedToken = token.trim().toUpperCase();
    if (!trimmedEmail) {
      toast.error("Please enter your email to verify.");
      return;
    }
    if (!trimmedToken || trimmedToken.length < 7) {
      toast.error("Please enter the full 6-character access code.");
      return;
    }
    verifyMutation.mutate({ email: trimmedEmail, token: trimmedToken });
  };

  if (checkingAuth) {
    return (
      <div className="flex justify-center p-12">
        <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

  if (step === "authenticated") {
    return (
      <Card className="my-6 border-border/40 bg-card/30 backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-6 border-b border-border/30 px-4 sm:px-6">
          <div>
            <CardTitle className="text-2xl font-bold">Manage Your Watches</CardTitle>
            <CardDescription className="text-sm mt-1">
              View and cancel your active watch requests.
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => logoutMutation.mutate()}
            className="ml-4 rounded-lg px-4 border-border/50 hover:bg-destructive/5 hover:text-destructive hover:border-destructive/30 transition-colors"
          >
            <LogOut className="h-4 w-4 mr-2" /> Logout
          </Button>
        </CardHeader>
        <CardContent className="px-4 sm:px-6 pt-8">
          <WatchDashboard />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-8 sm:py-12">
      <Card className="w-full max-w-md border-border/40 bg-card/30 backdrop-blur-sm overflow-hidden">
        <div className="p-8 sm:p-0">
          <CardHeader className="text-center sm:pt-8">
            <div className="mx-auto bg-primary/10 w-14 h-14 rounded-xl flex items-center justify-center mb-4">
              <Eye className="h-7 w-7 text-primary" />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight">Manage Watches</CardTitle>
            <CardDescription className="text-sm mt-2 px-4">
              {step === "email"
                ? "Enter your email to receive a secure access code."
                : "Enter the code sent to your email."}
            </CardDescription>
          </CardHeader>
        </div>
        <CardContent className="p-6 sm:p-8">
          {step === "email" ? (
            <form onSubmit={handleRequestCode} className="space-y-5">
              <div className="space-y-2">
                <Label
                  htmlFor="email"
                  className="text-xs font-bold uppercase tracking-widest text-muted-foreground ml-1"
                >
                  Email Address
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setEmail(e.target.value.trim())
                  }
                  required
                  className="h-12 text-base rounded-lg border-border/50 focus:border-primary/50 focus:ring-primary/20 transition-all bg-muted/20"
                />
              </div>
              <Button
                type="submit"
                className="w-full h-12 rounded-lg font-bold"
                disabled={requestMutation.isPending}
              >
                {requestMutation.isPending ? (
                  <Loader2 className="animate-spin mr-2 h-5 w-5" />
                ) : null}
                Send Access Code
              </Button>
            </form>
          ) : (
            <form onSubmit={handleVerifyCode} className="space-y-5">
              <div className="space-y-2">
                <Label
                  htmlFor="email"
                  className="text-xs font-bold uppercase tracking-widest text-muted-foreground ml-1"
                >
                  Confirm Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                  required
                  className="h-12 text-base rounded-lg bg-muted/40 opacity-70 cursor-not-allowed"
                  disabled={!!email && requestMutation.isSuccess}
                />
              </div>
              <div className="space-y-2">
                <Label
                  htmlFor="token"
                  className="text-xs font-bold uppercase tracking-widest text-muted-foreground ml-1"
                >
                  Access Code
                </Label>
                <Input
                  id="token"
                  type="text"
                  placeholder="XXX-XXX"
                  value={token}
                  onChange={handleTokenChange}
                  onPaste={(e) => {
                    // Handle paste events explicitly to sanitize whitespace
                    e.preventDefault();
                    const pasted = e.clipboardData.getData("text");
                    setToken(sanitizeToken(pasted));
                  }}
                  required
                  className="uppercase text-center tracking-[0.2em] font-mono text-2xl h-14 rounded-lg border-border/50 focus:border-primary/50 focus:ring-primary/20 transition-all bg-muted/20"
                  autoComplete="one-time-code"
                  inputMode="text"
                />
                <p className="text-xs text-muted-foreground text-center mt-1">
                  Paste your code — spaces are removed automatically
                </p>
              </div>
              <Button
                type="submit"
                className="w-full h-12 rounded-lg font-bold"
                disabled={verifyMutation.isPending}
              >
                {verifyMutation.isPending ? (
                  <Loader2 className="animate-spin mr-2 h-5 w-5" />
                ) : null}
                Verify Code
              </Button>
              <Button
                variant="link"
                type="button"
                className="w-full text-muted-foreground font-semibold"
                onClick={() => setStep("email")}
              >
                Use a different email
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ManageWatches;
