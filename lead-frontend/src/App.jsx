import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import CreateCampaign from './components/CreateCampaign';

// Base URL for your backend API
// IMPORTANT: For deployment, replace 'http://localhost:8000' with your actual backend URL.
const API_BASE_URL = 'http://localhost:8000'; 

function App() {
  const [activeSection, setActiveSection] = useState('dashboard'); // 'dashboard' or 'create-campaign'

  const renderContent = () => {
    switch (activeSection) {
      case 'dashboard':
        return <Dashboard apiBaseUrl={API_BASE_URL} />;
      case 'create-campaign':
        return <CreateCampaign apiBaseUrl={API_BASE_URL} />;
      default:
        return <Dashboard apiBaseUrl={API_BASE_URL} />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-100 font-sans antialiased">
      <Sidebar activeSection={activeSection} setActiveSection={setActiveSection} />

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto bg-gray-100">
        {renderContent()}
      </div>
    </div>
  );
}

export default App;
