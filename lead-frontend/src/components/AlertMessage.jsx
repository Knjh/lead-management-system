import React from 'react';
import { CircleCheck, XCircle } from 'lucide-react'; // Import icons

function AlertMessage({ type, message }) {
  const bgColor = type === 'success' ? 'bg-green-100' : 'bg-red-100';
  const textColor = type === 'success' ? 'text-green-800' : 'text-red-800';
  const Icon = type === 'success' ? CircleCheck : XCircle;

  return (
    <div
      className={`mt-6 p-4 rounded-lg text-sm flex items-center ${bgColor} ${textColor}`}
      role="alert"
    >
      <Icon className="w-5 h-5 mr-2" />
      {message}
    </div>
  );
}

export default AlertMessage;
