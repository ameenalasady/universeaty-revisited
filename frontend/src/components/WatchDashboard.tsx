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
        <div key={w.id} className="flex items-center justify-between p-4 border rounded-lg mb-3 bg-card">
            <div>
                <div className="font-semibold text-lg">{w.course_code} <span className="text-muted-foreground font-normal text-base">({w.section_display})</span></div>
                <div className="text-sm text-muted-foreground mt-1">Requested: {new Date(w.created_at + 'Z').toLocaleString()}</div>
                <div className="mt-2 flex gap-2">
                    {w.status === 'pending' && <Badge variant="secondary">Pending</Badge>}
                    {w.status === 'notified' && <Badge variant="default" className="bg-green-600 hover:bg-green-700">Notified</Badge>}
                    {w.status === 'error' && <Badge variant="destructive">Error</Badge>}
                    {w.status === 'cancelled' && <Badge variant="outline" className="text-muted-foreground">Cancelled</Badge>}
                </div>
            </div>
            {w.status !== 'cancelled' && (
                <Button 
                    variant="ghost" 
                    size="icon" 
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
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
    );

    return (
        <div className="space-y-8">
            <div>
                <h3 className="text-xl font-medium mb-4">Active Watches</h3>
                {activeWatches.length === 0 ? (
                    <p className="text-muted-foreground italic bg-muted/50 p-6 rounded-lg text-center">You don't have any active watches.</p>
                ) : (
                    activeWatches.map(renderWatch)
                )}
            </div>
            {cancelledWatches.length > 0 && (
                <div>
                    <h3 className="text-xl font-medium mb-4 text-muted-foreground">Cancelled</h3>
                    <div className="opacity-60">
                        {cancelledWatches.map(renderWatch)}
                    </div>
                </div>
            )}
        </div>
    );
};

export default WatchDashboard;
