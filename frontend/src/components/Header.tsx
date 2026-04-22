import React from 'react';

import { Button } from './ui/button';

interface HeaderProps {
    currentView?: 'home' | 'manage';
    onViewChange?: (view: 'home' | 'manage') => void;
}

export const Header: React.FC<HeaderProps> = ({ currentView = 'home', onViewChange }) => {
  return (
    <header className="pt-3 pb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-center sm:text-left">
      <div className="flex flex-col items-center sm:items-start">
        <h1 
           className="text-4xl sm:text-5xl font-bold tracking-tight cursor-pointer hover:opacity-80 transition-opacity"
           onClick={() => onViewChange && onViewChange('home')}
        >
          universeaty.ca
        </h1>
        <p className="text-muted-foreground mt-1 max-w-xl text-sm sm:text-base">
          Get notified when a seat opens up!
        </p>
      </div>
      
      {onViewChange && (
        <div className="flex shrink-0 justify-center">
           <Button 
              variant={currentView === 'manage' ? 'secondary' : 'outline'} 
              size={currentView === 'manage' ? 'default' : 'sm'}
              className="w-full sm:w-auto font-medium"
              onClick={() => onViewChange(currentView === 'manage' ? 'home' : 'manage')}
           >
               {currentView === 'manage' ? 'Back to Search' : 'Manage Watches'}
           </Button>
        </div>
      )}
    </header>
  );
};

export default Header;