import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Mail, Eye, XCircle } from 'lucide-react';
import { CourseDetailsSection } from '@/services/api';
import { toast } from 'sonner';

interface WatchSectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  section: CourseDetailsSection | null;
  termName: string;
  courseCode: string;
  onSubmit: (email: string) => void;
  isPending: boolean;
}

export const WatchSectionDialog: React.FC<WatchSectionDialogProps> = ({
  isOpen,
  onOpenChange,
  section,
  termName,
  courseCode,
  onSubmit,
  isPending,
}) => {
  const [email, setEmail] = useState('');
  const [isValidEmail, setIsValidEmail] = useState(false);

  // This effect runs when the dialog opens to pre-populate the email from localStorage
  useEffect(() => {
    if (isOpen) {
      const savedEmail = localStorage.getItem('universeaty_userEmail') || '';
      setEmail(savedEmail);
    }
  }, [isOpen]);

  // This effect validates the email whenever it changes, either from pre-population or user input.
  useEffect(() => {
    setIsValidEmail(email.trim() !== '' && /\S+@\S+\.\S+/.test(email));
  }, [email]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidEmail || isPending || !section) {
        if (!isValidEmail) toast.error("Invalid Email", { description: "Please enter a valid email address." });
        return;
    }
    onSubmit(email);
  };

  if (!section) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Watch Course Section</DialogTitle>
            <DialogDescription>
              Get notified via email when a seat opens in{" "}
              <span className="font-semibold">
                {courseCode} {section?.block_type} {section?.section} ({section?.key})
              </span>{" "}
              for the <span className="font-semibold">{termName}</span> term.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="email" className="text-right">
                Email
              </Label>
              <div className="col-span-3 relative">
                <Mail className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-8"
                  required
                  aria-required="true"
                  aria-label="Email address for notification"
                  disabled={isPending}
                />
              </div>
            </div>
          </div>
          <DialogFooter className="flex-col sm:flex-row sm:justify-end gap-2">
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={isPending}>
                <XCircle className="mr-2 h-4 w-4" /> Cancel
              </Button>
            </DialogClose>
            <Button
              type="submit"
              disabled={isPending || !isValidEmail}
              aria-label="Submit watch request for this section"
            >
              {isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              Watch This Section
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default WatchSectionDialog;