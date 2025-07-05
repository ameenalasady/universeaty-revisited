import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="pt-3 pb-6 text-center">
      <div>
        <h1 className="text-3xl sm:text-4xl tracking-tight">
          universeaty.ca
        </h1>
        <p className="text-muted-foreground mt-2 max-w-xl mx-auto">
          Get notified when a seat opens up!
        </p>
      </div>
    </header>
  );
};

export default Header;