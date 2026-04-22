import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { requestAuthCode, verifyAuthCode, logoutUser, getAuthStatus } from '../services/api';
import WatchDashboard from '../components/WatchDashboard';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { toast } from 'sonner';
import { Loader2, LogOut } from 'lucide-react';

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
            window.history.replaceState({}, document.title, window.location.pathname);
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
            <Card className="my-6 max-w-3xl mx-auto shadow-md">
                <CardHeader className="flex flex-row items-center justify-between pb-4 border-b mb-6">
                    <div>
                        <CardTitle className="text-2xl">Manage Your Watches</CardTitle>
                        <CardDescription className="text-base mt-1">View and cancel your active watch requests.</CardDescription>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => logoutMutation.mutate()} className="ml-4">
                        <LogOut className="h-4 w-4 mr-2" /> Logout
                    </Button>
                </CardHeader>
                <CardContent>
                    <WatchDashboard />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="my-6 max-w-md mx-auto shadow-md">
            <CardHeader className="text-center">
                <CardTitle className="text-2xl">Manage Watches</CardTitle>
                <CardDescription className="text-base mt-1">
                    {step === 'email' ? 'Enter your email to receive a secure access code.' : 'Enter the code sent to your email.'}
                </CardDescription>
            </CardHeader>
            <CardContent>
                {step === 'email' ? (
                    <form onSubmit={handleRequestCode} className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-base">Email Address</Label>
                            <Input 
                                id="email" 
                                type="email" 
                                placeholder="mcmaster@mcmaster.ca" 
                                value={email} 
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)} 
                                required 
                                className="text-base p-6"
                            />
                        </div>
                        <Button type="submit" className="w-full text-base py-6" disabled={requestMutation.isPending}>
                            {requestMutation.isPending ? <Loader2 className="animate-spin mr-2 h-5 w-5" /> : null}
                            Send Access Code
                        </Button>
                    </form>
                ) : (
                    <form onSubmit={handleVerifyCode} className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-base">Email Address</Label>
                            <Input 
                                id="email" 
                                type="email" 
                                value={email} 
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)} 
                                required 
                                className="text-base p-6"
                                disabled={!!email && requestMutation.isSuccess} 
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="token" className="text-base">Access Code</Label>
                            <Input 
                                id="token" 
                                type="text" 
                                placeholder="XXX-XXX" 
                                value={token} 
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setToken(e.target.value)} 
                                required 
                                className="uppercase text-center tracking-widest font-mono text-2xl p-6"
                                maxLength={7}
                            />
                        </div>
                        <Button type="submit" className="w-full text-base py-6" disabled={verifyMutation.isPending}>
                            {verifyMutation.isPending ? <Loader2 className="animate-spin mr-2 h-5 w-5" /> : null}
                            Verify Code
                        </Button>
                        <Button variant="link" type="button" className="w-full text-muted-foreground" onClick={() => setStep('email')}>
                            Use a different email
                        </Button>
                    </form>
                )}
            </CardContent>
        </Card>
    );
};

export default ManageWatches;
