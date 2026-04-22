import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { requestAuthCode, verifyAuthCode, logoutUser, getAuthStatus } from '../services/api';
import WatchDashboard from '../components/WatchDashboard';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { toast } from 'sonner';
import { Loader2, LogOut, Eye } from 'lucide-react';

export const ManageWatches: React.FC = () => {
    const [email, setEmail] = useState('');
    const [token, setToken] = useState('');
    const [step, setStep] = useState<'email' | 'code' | 'authenticated'>('email');
    const [checkingAuth, setCheckingAuth] = useState(true);
    const queryClient = useQueryClient();

    // Check for magic link token or existing session on mount
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const urlToken = urlParams.get('token');
        const urlEmail = urlParams.get('email');
        
        if (urlToken) {
            setToken(urlToken);
            if (urlEmail) setEmail(urlEmail);
            setStep('code');
            setCheckingAuth(false);
            // Clean up URL
            window.history.replaceState({}, document.title, window.location.pathname + '?view=manage');
        } else {
            // Check if already logged in
            getAuthStatus()
                .then((data) => {
                    setEmail(data.email);
                    setStep('authenticated');
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
            setStep('code');
        },
        onError: (err: any) => {
            toast.error(err.message || "Failed to send code");
        }
    });

    const verifyMutation = useMutation({
        mutationFn: verifyAuthCode,
        onSuccess: () => {
            toast.success("Successfully authenticated!");
            setStep('authenticated');
        },
        onError: (err: any) => {
            toast.error(err.message || "Invalid or expired code");
        }
    });

    const logoutMutation = useMutation({
        mutationFn: logoutUser,
        onSuccess: () => {
            toast.success("Logged out");
            setStep('email');
            setEmail('');
            setToken('');
            queryClient.clear();
        }
    });

    const handleRequestCode = (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) return;
        requestMutation.mutate({ email });
    };

    const handleVerifyCode = (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) {
            toast.error("Please enter your email to verify.");
            return;
        }
        verifyMutation.mutate({ email, token });
    };

    if (checkingAuth) {
        return (
            <div className="flex justify-center p-12">
                <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
            </div>
        );
    }

    if (step === 'authenticated') {
        return (
            <Card className="my-6 border-none sm:border shadow-none sm:shadow-md bg-transparent sm:bg-card">
                <CardHeader className="flex flex-row items-center justify-between pb-6 border-b border-muted/20 px-0 sm:px-6">
                    <div>
                        <CardTitle className="text-2xl sm:text-3xl font-bold">Manage Your Watches</CardTitle>
                        <CardDescription className="text-sm sm:text-base mt-1">View and cancel your active watch requests.</CardDescription>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => logoutMutation.mutate()} className="ml-4 rounded-full px-4 border-muted-foreground/30 hover:bg-destructive/5 hover:text-destructive hover:border-destructive/30 transition-colors">
                        <LogOut className="h-4 w-4 mr-2" /> Logout
                    </Button>
                </CardHeader>
                <CardContent className="px-0 sm:px-6 pt-8">
                    <WatchDashboard />
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center py-8 sm:py-12">
            <Card className="w-full max-w-md border-none sm:border shadow-none sm:shadow-xl bg-transparent sm:bg-card overflow-hidden">
                <div className="bg-primary/5 sm:bg-transparent p-8 sm:p-0">
                    <CardHeader className="text-center sm:pt-8">
                        <div className="mx-auto bg-primary/10 w-16 h-16 rounded-2xl flex items-center justify-center mb-4">
                            <Eye className="h-8 w-8 text-primary" />
                        </div>
                        <CardTitle className="text-3xl font-bold tracking-tight">Manage Watches</CardTitle>
                        <CardDescription className="text-base mt-2 px-4">
                            {step === 'email' ? 'Enter your email to receive a secure access code.' : 'Enter the code sent to your email.'}
                        </CardDescription>
                    </CardHeader>
                </div>
                <CardContent className="p-8">
                    {step === 'email' ? (
                        <form onSubmit={handleRequestCode} className="space-y-6">
                            <div className="space-y-2">
                                <Label htmlFor="email" className="text-xs font-bold uppercase tracking-widest text-muted-foreground ml-1">Email Address</Label>
                                <Input 
                                    id="email" 
                                    type="email" 
                                    placeholder="your@email.com" 
                                    value={email} 
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)} 
                                    required 
                                    className="text-lg p-6 rounded-xl border-muted/50 focus:border-primary/50 focus:ring-primary/20 transition-all bg-muted/20"
                                />
                            </div>
                            <Button type="submit" className="w-full text-lg py-7 rounded-xl font-bold shadow-lg shadow-primary/20" disabled={requestMutation.isPending}>
                                {requestMutation.isPending ? <Loader2 className="animate-spin mr-2 h-5 w-5" /> : null}
                                Send Access Code
                            </Button>
                        </form>
                    ) : (
                        <form onSubmit={handleVerifyCode} className="space-y-6">
                            <div className="space-y-2">
                                <Label htmlFor="email" className="text-xs font-bold uppercase tracking-widest text-muted-foreground ml-1">Confirm Email</Label>
                                <Input 
                                    id="email" 
                                    type="email" 
                                    value={email} 
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)} 
                                    required 
                                    className="text-lg p-6 rounded-xl bg-muted/40 opacity-70 cursor-not-allowed"
                                    disabled={!!email && requestMutation.isSuccess} 
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="token" className="text-xs font-bold uppercase tracking-widest text-muted-foreground ml-1">Access Code</Label>
                                <Input 
                                    id="token" 
                                    type="text" 
                                    placeholder="XXX-XXX" 
                                    value={token} 
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setToken(e.target.value)} 
                                    required 
                                    className="uppercase text-center tracking-[0.2em] font-mono text-3xl p-8 rounded-xl border-muted/50 focus:border-primary/50 focus:ring-primary/20 transition-all bg-muted/20"
                                    maxLength={7}
                                />
                            </div>
                            <Button type="submit" className="w-full text-lg py-7 rounded-xl font-bold shadow-lg shadow-primary/20" disabled={verifyMutation.isPending}>
                                {verifyMutation.isPending ? <Loader2 className="animate-spin mr-2 h-5 w-5" /> : null}
                                Verify Code
                            </Button>
                            <Button variant="link" type="button" className="w-full text-muted-foreground font-semibold" onClick={() => setStep('email')}>
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
