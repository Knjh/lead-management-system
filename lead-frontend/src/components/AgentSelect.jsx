import React from 'react';
import { Users, XCircle } from 'lucide-react'; // Import icons

function AgentSelect({ agents, selectedAgent, handleAgentChange, loading, error }) {
  const onAgentChange = (event) => {
    handleAgentChange(event.target.value);
  };

  return (
    <div className="mb-6">
      <label htmlFor="agent-select" className="block text-gray-700 text-sm font-medium mb-2">
        Select Agent:
      </label>
      {loading ? (
        <p className="text-gray-500 flex items-center"><Users className="w-4 h-4 mr-2"/> Loading agents...</p>
      ) : error ? (
        <p className="text-red-600 flex items-center"><XCircle className="w-4 h-4 mr-2"/> Error: {error}</p>
      ) : agents.length === 0 ? (
        <p className="text-gray-500">No agents available. Please configure agents in Retell AI.</p>
      ) : (
        <select
          id="agent-select"
          value={selectedAgent}
          onChange={onAgentChange}
          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md shadow-sm"
        >
          {agents.map((agent) => (
            // Use agent.id for the key prop and display agent.name (which now comes from agent_name)
            <option key={agent.id} value={agent.id}>
              {agent.name || agent.id} 
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

export default AgentSelect;
