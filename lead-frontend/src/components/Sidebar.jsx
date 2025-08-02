import React from 'react';
import { LayoutDashboard, Rocket } from 'lucide-react'; // Import icons

function Sidebar({ activeSection, setActiveSection }) {
  return (
    <div className="w-64 bg-gray-800 text-white flex flex-col p-4 shadow-lg">
      <div className="text-2xl font-bold mb-8 text-center text-blue-400">
        Lead Manager
      </div>
      <nav className="flex-1">
        <ul>
          <li className="mb-2">
            <button
              onClick={() => setActiveSection('dashboard')}
              className={`flex items-center w-full p-3 rounded-lg text-left transition-colors duration-200
                ${activeSection === 'dashboard' ? 'bg-blue-600 text-white shadow-md' : 'hover:bg-gray-700 text-gray-300'}`}
            >
              <LayoutDashboard className="w-5 h-5 mr-3" />
              Dashboard
            </button>
          </li>
          <li className="mb-2">
            <button
              onClick={() => setActiveSection('create-campaign')}
              className={`flex items-center w-full p-3 rounded-lg text-left transition-colors duration-200
                ${activeSection === 'create-campaign' ? 'bg-blue-600 text-white shadow-md' : 'hover:bg-gray-700 text-gray-300'}`}
            >
              <Rocket className="w-5 h-5 mr-3" />
              Create Campaign
            </button>
          </li>
        </ul>
      </nav>
      <div className="text-xs text-gray-500 text-center mt-auto p-2">
        &copy; {new Date().getFullYear()} Lead Manager.
      </div>
    </div>
  );
}

export default Sidebar;
