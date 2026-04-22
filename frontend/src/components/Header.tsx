import React from 'react';

import { Button } from './ui/button';

interface HeaderProps {
    currentView?: 'home' | 'manage';
    onViewChange?: (view: 'home' | 'manage') => void;
}

export const Header: React.FC<HeaderProps> = ({ currentView = 'home', onViewChange }) => {
  return (
    <header className="pt-3 pb-6 flex items-center justify-between">
      <div className="text-left">
        <h1 
           className="text-3xl sm:text-4xl tracking-tight cursor-pointer"
           onClick={() => onViewChange && onViewChange('home')}
        >
          universeaty.ca
        </h1>
        <p className="text-muted-foreground mt-2 max-w-xl">
          Get notified when a seat opens up!
        </p>
      </div>
      
      {onViewChange && (
        <div>
           <Button 
              variant={currentView === 'manage' ? 'secondary' : 'outline'} 
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