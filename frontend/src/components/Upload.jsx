import React, { useState } from 'react';
import { Upload as UploadIcon, FileText, AlertCircle } from 'lucide-react';
import CreateProject from './CreateProject';

const API_URL = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

function Upload({ projects = [], functionalAreas = [], onProjectCreated }) {
  const [selectedProject, setSelectedProject] = useState('');
  const [selectedArea, setSelectedArea] = useState('');
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [showCreateProject, setShowCreateProject] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(droppedFiles);
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setUploadStatus({ type: 'error', message: 'Please select files to upload' });
      return;
    }

    if (!selectedArea) {
      setUploadStatus({ type: 'error', message: 'Please select a functional area' });
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      formData.append('functional_area', selectedArea);
      if (selectedProject && selectedProject !== 'global') {
        formData.append('project_id', selectedProject);
      }

      const response = await fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setUploadStatus({
          type: 'success',
          message: `Upload successful! Job ID: ${data.job_id}`,
          jobId: data.job_id
        });
        setFiles([]);
      } else {
        setUploadStatus({
          type: 'error',
          message: data.detail || 'Upload failed'
        });
      }
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: `Upload error: ${error.message}`
      });
    } finally {
      setUploading(false);
    }
  };

  const handleProjectCreated = async (newProject) => {
    // Close the modal
    setShowCreateProject(false);
    
    // Call the parent's refresh function to update the project list
    if (onProjectCreated) {
      await onProjectCreated();
    }
    
    // Automatically select the newly created project
    if (newProject && newProject.id) {
      setSelectedProject(newProject.id);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Upload Documents</h1>

      {/* Project Selection */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <label className="block text-sm font-medium text-gray-700">
            Select Project
          </label>
          <button
            onClick={() => setShowCreateProject(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            + New Project
          </button>
        </div>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Select a project...</option>
          <option value="global">🌐 Global (All Customers)</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.customer} - {project.name}
            </option>
          ))}
        </select>
      </div>

      {/* Functional Area Selection */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-4">
          Functional Area
        </label>
        <select
          value={selectedArea}
          onChange={(e) => setSelectedArea(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Select functional area...</option>
          {functionalAreas.map((area) => (
            <option key={area} value={area}>
              {area}
            </option>
          ))}
        </select>
      </div>

      {/* File Upload Area */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-500 transition-colors"
        >
          <UploadIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-lg text-gray-600 mb-2">
            Drag and drop files here, or click to select
          </p>
          <p className="text-sm text-gray-500 mb-4">
            Supported formats: .xlsx, .xls, .pdf, .docx, .txt
          </p>
          <input
            type="file"
            multiple
            accept=".xlsx,.xls,.pdf,.docx,.txt"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer"
          >
            Select Files
          </label>
        </div>

        {/* Selected Files */}
        {files.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Selected Files ({files.length})
            </h3>
            <div className="space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center">
                    <FileText className="h-5 w-5 text-blue-600 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{file.name}</p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setFiles(files.filter((_, i) => i !== index))}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upload Button */}
        <div className="mt-6">
          <button
            onClick={handleUpload}
            disabled={uploading || files.length === 0}
            className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
          >
            {uploading ? 'Uploading...' : 'Upload Files'}
          </button>
        </div>

        {/* Upload Status */}
        {uploadStatus && (
          <div
            className={`mt-4 p-4 rounded-lg ${
              uploadStatus.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            <div className="flex items-start">
              {uploadStatus.type === 'error' && (
                <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <p className="font-medium">{uploadStatus.message}</p>
                {uploadStatus.jobId && (
                  <p className="text-sm mt-2">
                    View progress on the{' '}
                    <a href="/status" className="underline font-medium">
                      Status page
                    </a>
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showCreateProject && (
        <CreateProject
          onClose={() => setShowCreateProject(false)}
          onProjectCreated={handleProjectCreated}
        />
      )}
    </div>
  );
}

export default Upload;
