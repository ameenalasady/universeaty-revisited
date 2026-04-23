import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getUserWatches, cancelUserWatch, UserWatch } from '../services/api';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Loader2, Trash2 } from 'lucide-react';
import { Badge } from '../components/ui/badge';

export const WatchDashboard: React.FC = () => {
    const queryClient = useQueryClient();

    const { data: watches, isLoading, isError } = useQuery<UserWatch[]>({
        queryKey: ['userWatches'],
        queryFn: getUserWatches,
        retry: false, // Don't retry if unauthorized
    });

    const cancelMutation = useMutation({
        mutationFn: cancelUserWatch,
        onSuccess: () => {
            toast.success("Watch request cancelled");
            queryClient.invalidateQueries({ queryKey: ['userWatches'] });
        },
        onError: () => {
            toast.error("Failed to cancel watch request");
        }
    });

    if (isLoading) {
        return <div className="flex justify-center p-8"><Loader2 className="animate-spin text-muted-foreground" /></div>;
    }

    if (isError) {
        return <div className="text-destructive p-4 text-center">Failed to load watches. Please try logging in again.</div>;
    }

    const activeWatches = watches?.filter(w => w.status !== 'cancelled') || [];
    const cancelledWatches = watches?.filter(w => w.status === 'cancelled') || [];

    const renderWatch = (w: UserWatch) => (
        <div key={w.id} className="group relative border border-border/40 rounded-xl p-5 mb-4 bg-muted/20 backdrop-blur-sm transition-all hover:border-primary/30 hover:bg-muted/40">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <span className="font-bold text-xl tracking-tight">{w.course_code}</span>
                        <span className="text-muted-foreground font-medium">{w.section_display}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium mt-0.5">
                        <span className="opacity-70">Requested</span>
                        <span className="bg-muted/50 border border-border/40 px-2 py-0.5 rounded-md text-[10px] uppercase font-bold tracking-wider">
                           {new Date(w.created_at + 'Z').toLocaleDateString()}
                        </span>
                    </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-none border-muted/20">
                    <div className="flex gap-2">
                        {w.status === 'pending' && (
                            <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20 font-bold px-3 py-1 rounded-md">
                                Pending
                            </Badge>
                        )}
                        {w.status === 'notified' && (
                            <Badge variant="default" className="border-transparent bg-green-500/20 text-green-300 hover:bg-green-500/30 font-bold px-3 py-1 rounded-md">
                                Notified
                            </Badge>
                        )}
                        {w.status === 'error' && (
                            <Badge variant="destructive" className="border-transparent bg-red-500/20 text-red-300 hover:bg-red-500/30 font-bold px-3 py-1 rounded-md">
                                Error
                            </Badge>
                        )}
                        {w.status === 'cancelled' && (
                            <Badge variant="outline" className="text-muted-foreground font-bold px-3 py-1 border-dashed rounded-md">
                                Cancelled
                            </Badge>
                        )}
                    </div>

                    {w.status !== 'cancelled' && (
                        <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-10 w-10 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-full transition-colors"
                            onClick={() => cancelMutation.mutate(w.id)}
                            disabled={cancelMutation.isPending}
                        >
                            {cancelMutation.isPending && cancelMutation.variables === w.id ? (
                                <Loader2 className="h-5 w-5 animate-spin" />
                            ) : (
                                <Trash2 className="h-5 w-5" />
                            )}
                        </Button>
                    )}
                </div>
            </div>
        </div>
    );

    return (
        <div className="space-y-8">
            <div>
                <h3 className="text-lg font-semibold tracking-tight mb-4">Active Watches</h3>
                {activeWatches.length === 0 ? (
                    <p className="text-muted-foreground italic bg-muted/50 p-6 rounded-lg text-center">You don't have any active watches.</p>
                ) : (
                    activeWatches.map(renderWatch)
                )}
            </div>
            {cancelledWatches.length > 0 && (
                <div>
                    <h3 className="text-lg font-semibold tracking-tight mb-4 text-muted-foreground">Cancelled</h3>
                    <div className="opacity-60">
                        {cancelledWatches.map(renderWatch)}
                    </div>
                </div>
            )}
        </div>
    );
};

export default WatchDashboard;
