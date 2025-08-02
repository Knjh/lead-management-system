import React from 'react';
import { UploadCloud } from 'lucide-react'; // Import icon

function FileUpload({ selectedFile, handleFileChange }) {
  const onFileChange = (event) => {
    handleFileChange(event.target.files[0]);
  };

  return (
    <div className="mb-6">
      <label htmlFor="csv-upload" className="block text-gray-700 text-sm font-medium mb-2">
        Upload Leads CSV:
      </label>
      <div className="flex items-center space-x-3">
        <input
          type="file"
          id="csv-upload"
          accept=".csv"
          onChange={onFileChange}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100 cursor-pointer
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
        />
        {/* Optional: Display a small icon next to the file input */}
        <UploadCloud className="w-6 h-6 text-gray-400" />
      </div>
      {selectedFile && (
        <p className="mt-2 text-sm text-gray-600">
          Selected: <span className="font-medium">{selectedFile.name}</span>
        </p>
      )}
    </div>
  );
}

export default FileUpload;
