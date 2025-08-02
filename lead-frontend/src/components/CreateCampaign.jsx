import React, { useState, useEffect } from 'react';
import FileUpload from './FileUpload';
import AgentSelect from './AgentSelect';
import AlertMessage from './AlertMessage';
import { CircleCheck, XCircle } from 'lucide-react';

function CreateCampaign({ apiBaseUrl }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [agentLoading, setAgentLoading] = useState(true);
  const [agentError, setAgentError] = useState(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/agents`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        setAgents(data);
        // REMOVED: The line that automatically selected the first agent.
        // The 'selectedAgent' state will now remain empty until the user makes a choice.
      } catch (e) {
        setAgentError(e.message);
      } finally {
        setAgentLoading(false);
      }
    };
    fetchAgents();
  }, [apiBaseUrl]);

  const handleCreateCampaign = async () => {
    if (!selectedFile) {
      setMessage('Please select a CSV file to upload.');
      setMessageType('error');
      return;
    }
    if (!selectedAgent) {
      setMessage('Please select an agent for the campaign.');
      setMessageType('error');
      return;
    }

    setLoading(true);
    setMessage('');
    setMessageType('');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('agent_id', selectedAgent);

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/upload-leads`, { 
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setMessage(`Campaign created! Processed ${data.lead_ids.length} leads.`);
        setMessageType('success');
        setSelectedFile(null); 
      } else {
        const errorData = await response.json();
        setMessage(`Campaign creation failed: ${errorData.detail || 'Unknown error'}`);
        setMessageType('error');
      }
    } catch (error) {
      console.error('Network or unexpected error:', error);
      setMessage(`An error occurred: ${error.message}`);
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-semibold text-gray-800 mb-6">Create New Campaign</h2>
      <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-2xl mx-auto">
        
        <AgentSelect
          agents={agents}
          selectedAgent={selectedAgent}
          handleAgentChange={setSelectedAgent}
          loading={agentLoading}
          error={agentError}
        />

        <FileUpload
          selectedFile={selectedFile}
          handleFileChange={setSelectedFile}
        />

        <button
          onClick={handleCreateCampaign}
          disabled={!selectedFile || !selectedAgent || loading}
          className={`w-full py-3 px-4 rounded-lg font-semibold text-white transition-all duration-200
            ${(!selectedFile || !selectedAgent || loading)
              ? 'bg-blue-300 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
            }`}
        >
          {loading ? 'Creating Campaign...' : 'Create Campaign'}
        </button>

        {message && (
          <AlertMessage type={messageType} message={message} />
        )}

        <div className="mt-8 text-center text-gray-500 text-xs">
          <p>Mandatory CSV columns: "name", "phone_number"</p>
          <p>Optional CSV columns: "email", "company" (or "organization")</p>
        </div>
      </div>
    </div>
  );
}

export default CreateCampaign;
