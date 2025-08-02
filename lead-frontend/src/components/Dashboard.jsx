import React, { useState, useEffect } from 'react';
import AgentCard from './AgentCard'; // Import AgentCard

function Dashboard({ apiBaseUrl }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/agents`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // --- DEBUG LOG: Inspect the data received by Dashboard.jsx ---
        console.log("Dashboard.jsx: Fetched Agents Data:", data);
        // --- END DEBUG LOG ---

        setAgents(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchAgents();
  }, [apiBaseUrl]); // Depend on apiBaseUrl

  if (loading) return <div className="text-center p-8 text-gray-600">Loading agents...</div>;
  if (error) return <div className="text-center p-8 text-red-600">Error loading agents: {error}</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-semibold text-gray-800 mb-6">Agent Dashboard</h2>
      {agents.length === 0 ? (
        <p className="text-gray-600">No agents found. Please ensure agents are configured in your backend.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            // Ensure agent.id is used for the key prop
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}

export default Dashboard;
