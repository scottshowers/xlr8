import React, { useState, useEffect } from 'react';
import { Upload as UploadIcon, FileText, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import CreateProject from './CreateProject';

const API_URL = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

function Upload({ projects = [], functionalAreas = [], onProjectCreated }) {
  const [selectedProject, setSelectedProject] = useState('');
  const [selectedArea, setSelectedArea] = useState('');
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [currentJobId, setCurrentJobId] = useState(null);
  const [progress, setProgress] = useState({ percent: 0, step: '' });

  // Poll job status for progress updates
  useEffect(() => {
    if (!currentJobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/jobs/${currentJobId}`);
        if (response.ok) {
          const job = await response.json();
          
          // Update progress
          if (job.progress) {
            setProgress({
              percent: job.progress.percent || 0,
              step: job.progress.step || ''
            });
          }

          // Check if completed or failed
          if (job.status === 'completed') {
            clearInterval(pollInterval);
            setProgress({ percent: 100, step: 'Complete!' });
            setUploadStatus({
              type: 'success',
              message: `Upload successful! File processed.`
            });
            setUploading(false);
            setCurrentJobId(null);
            setFiles([]);
          } else if (job.status === 'failed') {
            clearInterval(pollInterval);
            setUploadStatus({
              type: 'error',
              message: job.error_message || 'Upload failed'
            });
            setUploading(false);
            setCurrentJobId(null);
          }
        }
      } catch (error) {
        console.error('Error polling job status:', error);
      }
    }, 1000); // Poll every second

    return () => clearInterval(pollInterval);
  }, [currentJobId]);

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
      setUploadStatus({ type: 'error', message: 'Please select a file to upload' });
      return;
    }

    if (!selectedArea) {
      setUploadStatus({ type: 'error', message: 'Please select a functional area' });
      return;
    }

    // Get project value - use selected or default to 'global'
    const projectValue = selectedProject || 'global';

    setUploading(true);
    setUploadStatus(null);
    setProgress({ percent: 0, step: 'Starting upload...' });

    try {
      // Backend only handles ONE file at a time
      const file = files[0];

      const formData = new FormData();
      formData.append('file', file); // ✅ Singular "file"
      formData.append('project', projectValue); // ✅ "project" not "project_id"
      formData.append('functional_area', selectedArea);

      const response = await fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        // Start polling for progress
        setCurrentJobId(data.job_id);
        setProgress({ percent: 5, step: 'Processing...' });
      } else {
        setUploadStatus({
          type: 'error',
          message: data.detail || 'Upload failed'
        });
        setUploading(false);
      }
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: `Upload error: ${error.message}`
      });
      setUploading(false);
    }
  };

  const handleProjectCreated = async (newProject) => {
    setShowCreateProject(false);
    
    if (onProjectCreated) {
      await onProjectCreated();
    }
    
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
            <option key={project.id} value={project.name}>
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
            Drag and drop a file here, or click to select
          </p>
          <p className="text-sm text-gray-500 mb-4">
            Supported formats: .xlsx, .xls, .pdf, .docx, .txt
          </p>
          <input
            type="file"
            accept=".xlsx,.xls,.pdf,.docx,.txt,.md"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer"
          >
            Select File
          </label>
        </div>

        {/* Selected File */}
        {files.length > 0 && !uploading && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Selected File
            </h3>
            <div className="space-y-2">
              {files.slice(0, 1).map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center">
                    <FileText className="h-5 w-5 text-blue-600 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{file.name}</p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setFiles([])}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
            {files.length > 1 && (
              <p className="text-sm text-amber-600 mt-2">
                Note: Only the first file will be uploaded. Multiple files coming soon!
              </p>
            )}
          </div>
        )}

        {/* Progress Bar */}
        {uploading && (
          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
                <span className="text-sm font-medium text-gray-700">
                  {progress.step || 'Processing...'}
                </span>
              </div>
              <span className="text-sm font-medium text-gray-700">
                {progress.percent}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress.percent}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Processing your file... This may take a minute for large documents.
            </p>
          </div>
        )}

        {/* Upload Button */}
        {!uploading && (
          <div className="mt-6">
            <button
              onClick={handleUpload}
              disabled={uploading || files.length === 0}
              className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
            >
              Upload File
            </button>
          </div>
        )}

        {/* Upload Status */}
        {uploadStatus && !uploading && (
          <div
            className={`mt-4 p-4 rounded-lg ${
              uploadStatus.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            <div className="flex items-start">
              {uploadStatus.type === 'error' ? (
                <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5" />
              ) : (
                <CheckCircle className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <p className="font-medium">{uploadStatus.message}</p>
                {uploadStatus.type === 'success' && (
                  <p className="text-sm mt-2">
                    View your document on the{' '}
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
