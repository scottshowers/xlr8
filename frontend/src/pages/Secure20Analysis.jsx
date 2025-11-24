import React, { useState } from 'react';
import { Upload, FileSpreadsheet, TrendingUp, AlertCircle } from 'lucide-react';

function Secure20Analysis() {
  const [companyName, setCompanyName] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Check if it's an Excel file
      const validTypes = [
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      ];
      
      if (validTypes.includes(selectedFile.type) || selectedFile.name.endsWith('.xlsx') || selectedFile.name.endsWith('.xls')) {
        setFile(selectedFile);
        setError('');
      } else {
        setError('Please select a valid Excel file (.xlsx or .xls)');
        setFile(null);
      }
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      const validTypes = [
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      ];
      
      if (validTypes.includes(droppedFile.type) || droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls')) {
        setFile(droppedFile);
        setError('');
      } else {
        setError('Please select a valid Excel file (.xlsx or .xls)');
        setFile(null);
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleSubmit = async () => {
    if (!companyName.trim()) {
      setError('Please enter a company name');
      return;
    }
    
    if (!file) {
      setError('Please select an Excel file');
      return;
    }

    setUploading(true);
    setError('');

    try {
      // TODO: Implement actual upload logic
      console.log('Uploading file:', file.name, 'for company:', companyName);
      
      // Simulate upload
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      alert('File uploaded successfully! Analysis starting...');
    } catch (err) {
      setError('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: '3rem', animation: 'fadeIn 0.8s ease-out 0.1s both' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.75rem' }}>
          <div style={{
            width: '56px',
            height: '56px',
            background: 'linear-gradient(135deg, #83b16d, #93abd9)',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(131, 177, 109, 0.25)'
          }}>
            <TrendingUp size={32} color="white" />
          </div>
          <div>
            <h1 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '3.5rem',
              fontWeight: '700',
              color: '#2a3441',
              margin: 0,
              letterSpacing: '-0.02em',
              lineHeight: '1.1'
            }}>
              SECURE <span style={{
                background: 'linear-gradient(135deg, #83b16d, #2766b1)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>2.0 Analysis</span>
            </h1>
            <p style={{
              color: '#5f6c7b',
              fontSize: '1.15rem',
              fontWeight: '500',
              margin: '0.5rem 0 0 0'
            }}>
              ROTH Catch-up Compliance Engine
            </p>
          </div>
        </div>
      </div>

      {/* Company Name Card */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e1e8ed',
        borderRadius: '16px',
        padding: '2.5rem',
        marginBottom: '2rem',
        boxShadow: '0 1px 3px rgba(42, 52, 65, 0.06)',
        animation: 'fadeIn 0.8s ease-out 0.2s both',
        transition: 'all 0.3s ease',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          content: '',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '3px',
          background: 'linear-gradient(90deg, #83b16d, #93abd9, #b2d6de)',
          opacity: companyName ? 1 : 0,
          transition: 'opacity 0.3s ease'
        }} />
        
        <label style={{
          display: 'block',
          marginBottom: '0.625rem',
          color: '#5f6c7b',
          fontSize: '0.875rem',
          fontWeight: '600',
          textTransform: 'uppercase',
          letterSpacing: '0.05em'
        }}>
          Company Name
        </label>
        <input
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder="Enter company name..."
          style={{
            width: '100%',
            padding: '0.875rem 1.125rem',
            background: '#f0f4f7',
            border: '1.5px solid #e1e8ed',
            borderRadius: '10px',
            color: '#2a3441',
            fontFamily: "'Manrope', sans-serif",
            fontSize: '0.95rem',
            transition: 'all 0.3s ease',
            outline: 'none'
          }}
          onFocus={(e) => {
            e.target.style.background = '#ffffff';
            e.target.style.borderColor = '#83b16d';
            e.target.style.boxShadow = '0 0 0 3px rgba(131, 177, 109, 0.1)';
          }}
          onBlur={(e) => {
            e.target.style.background = '#f0f4f7';
            e.target.style.borderColor = '#e1e8ed';
            e.target.style.boxShadow = 'none';
          }}
        />
      </div>

      {/* File Upload Card */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e1e8ed',
        borderRadius: '16px',
        padding: '2.5rem',
        marginBottom: '2rem',
        boxShadow: '0 1px 3px rgba(42, 52, 65, 0.06)',
        animation: 'fadeIn 0.8s ease-out 0.3s both',
        transition: 'all 0.3s ease',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          content: '',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '3px',
          background: 'linear-gradient(90deg, #83b16d, #93abd9, #b2d6de)',
          opacity: file ? 1 : 0,
          transition: 'opacity 0.3s ease'
        }} />

        <h3 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1.5rem',
          fontWeight: '700',
          color: '#2a3441',
          letterSpacing: '-0.02em',
          marginBottom: '1.5rem'
        }}>
          Excel File Upload
        </h3>

        {/* Dropzone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          style={{
            border: '2.5px dashed #e1e8ed',
            borderRadius: '16px',
            padding: '4rem 2rem',
            textAlign: 'center',
            background: 'linear-gradient(135deg, #f0f4f7 0%, #ffffff 100%)',
            transition: 'all 0.4s ease',
            cursor: 'pointer',
            position: 'relative'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = '#83b16d';
            e.currentTarget.style.background = '#ffffff';
            e.currentTarget.style.transform = 'scale(1.01)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = '#e1e8ed';
            e.currentTarget.style.background = 'linear-gradient(135deg, #f0f4f7 0%, #ffffff 100%)';
            e.currentTarget.style.transform = 'scale(1)';
          }}
        >
          <div style={{
            fontSize: '4rem',
            marginBottom: '1.5rem',
            opacity: 0.5,
            transition: 'all 0.3s ease'
          }}>
            📊
          </div>
          
          <p style={{
            color: '#2a3441',
            fontWeight: '600',
            marginBottom: '0.5rem',
            fontSize: '1.15rem'
          }}>
            Drop Excel file here
          </p>
          <p style={{
            color: '#5f6c7b',
            fontSize: '0.95rem',
            marginBottom: '1.5rem'
          }}>
            or click to browse
          </p>
          
          <input
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            style={{
              display: 'inline-block',
              padding: '0.875rem 1.75rem',
              background: 'transparent',
              border: '2px solid #83b16d',
              borderRadius: '10px',
              color: '#83b16d',
              fontFamily: "'Manrope', sans-serif",
              fontWeight: '700',
              fontSize: '0.95rem',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(131, 177, 109, 0.05)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(131, 177, 109, 0.15)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            Browse Files
          </label>

          <p style={{
            fontSize: '0.85rem',
            color: '#5f6c7b',
            marginTop: '1.5rem'
          }}>
            5 tabs required: Wages, Earnings, Deductions, Employee Deductions, Employee Earnings
          </p>
        </div>

        {/* Selected File Display */}
        {file && (
          <div style={{
            marginTop: '2rem',
            padding: '1.25rem 1.5rem',
            background: '#f0f4f7',
            border: '1.5px solid #e1e8ed',
            borderRadius: '12px',
            animation: 'slideIn 0.4s ease-out',
            transition: 'all 0.3s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#ffffff';
            e.currentTarget.style.borderColor = '#83b16d';
            e.currentTarget.style.boxShadow = '0 2px 8px rgba(131, 177, 109, 0.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#f0f4f7';
            e.currentTarget.style.borderColor = '#e1e8ed';
            e.currentTarget.style.boxShadow = 'none';
          }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
              <div style={{
                width: '48px',
                height: '48px',
                background: 'linear-gradient(135deg, #b2d6de, #93abd9)',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <FileSpreadsheet size={24} color="white" />
              </div>
              <div>
                <div style={{
                  fontWeight: '600',
                  color: '#2a3441',
                  marginBottom: '0.25rem'
                }}>
                  {file.name}
                </div>
                <div style={{
                  fontSize: '0.85rem',
                  color: '#5f6c7b'
                }}>
                  {(file.size / 1024).toFixed(1)} KB • Excel Spreadsheet
                </div>
              </div>
            </div>
            <button
              onClick={() => setFile(null)}
              style={{
                padding: '0.5rem 1rem',
                background: 'transparent',
                border: 'none',
                color: '#5f6c7b',
                fontWeight: '600',
                cursor: 'pointer',
                borderRadius: '6px',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#fef2f2';
                e.currentTarget.style.color = '#b91c1c';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = '#5f6c7b';
              }}
            >
              Remove
            </button>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div style={{
            marginTop: '1.5rem',
            display: 'flex',
            alignItems: 'start',
            gap: '1rem',
            padding: '1.25rem 1.5rem',
            background: '#fef2f2',
            border: '1px solid #fca5a5',
            borderRadius: '12px',
            color: '#b91c1c'
          }}>
            <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '0.125rem' }} />
            <div style={{ fontSize: '0.9rem' }}>{error}</div>
          </div>
        )}

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={uploading || !companyName || !file}
          style={{
            width: '100%',
            marginTop: '2rem',
            padding: '0.875rem 1.75rem',
            background: uploading || !companyName || !file ? '#e1e8ed' : 'linear-gradient(135deg, #83b16d, #93abd9)',
            border: 'none',
            borderRadius: '10px',
            color: 'white',
            fontFamily: "'Manrope', sans-serif",
            fontWeight: '700',
            fontSize: '0.95rem',
            cursor: uploading || !companyName || !file ? 'not-allowed' : 'pointer',
            transition: 'all 0.3s ease',
            boxShadow: uploading || !companyName || !file ? 'none' : '0 4px 12px rgba(131, 177, 109, 0.25)',
            position: 'relative',
            overflow: 'hidden',
            opacity: uploading || !companyName || !file ? 0.5 : 1
          }}
          onMouseEnter={(e) => {
            if (!uploading && companyName && file) {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(131, 177, 109, 0.35)';
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = uploading || !companyName || !file ? 'none' : '0 4px 12px rgba(131, 177, 109, 0.25)';
          }}
        >
          {uploading ? 'Processing...' : 'Start Analysis'}
        </button>
      </div>

      {/* Info Banner */}
      <div style={{
        display: 'flex',
        alignItems: 'start',
        gap: '1rem',
        padding: '1.25rem 1.5rem',
        background: 'linear-gradient(135deg, rgba(147, 171, 217, 0.08), rgba(178, 214, 222, 0.06))',
        border: '1px solid rgba(147, 171, 217, 0.2)',
        borderRadius: '12px',
        fontSize: '0.9rem',
        color: '#5f6c7b',
        animation: 'fadeIn 0.8s ease-out 0.4s both'
      }}>
        <span style={{ fontSize: '1.25rem', flexShrink: 0 }}>ℹ️</span>
        <div>
          The Excel file will be analyzed for SECURE 2.0 ROTH catch-up compliance. Please ensure all required tabs are present: Wages, Earnings, Deductions, Employee Deductions, and Employee Earnings.
        </div>
      </div>
    </div>
  );
}

export default Secure20Analysis;
