import React from 'react';
import { Users } from 'lucide-react'; // Import icon

function AgentCard({ agent }) {
  // Ensure agent object and its properties exist before accessing
  if (!agent) {
    return null; // Or render a placeholder for missing agent data
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 flex items-start space-x-4">
      <div className="flex-shrink-0 p-3 bg-blue-100 rounded-full text-blue-600">
        <Users className="w-6 h-6" />
      </div>
      <div className="flex-grow">
        {/* Display agent name, fallback to "Unnamed Agent" if name is null */}
        <h3 className="text-xl font-semibold text-blue-700 mb-1">{agent.name || 'Unnamed Agent'}</h3>
        {/* Display agent ID */}
        <p className="text-gray-600 text-sm mb-1">ID: <span className="font-mono text-gray-700">{agent.id}</span></p>
        {/* Removed status display as it's not provided by Retell AI /list-agents */}
      </div>
    </div>
  );
}

export default AgentCard;
