import { useState } from 'react';
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, Download, TrendingUp, Loader2 } from 'lucide-react';

export default function Secure20Analysis() {
  const [file, setFile] = useState(null);
  const [companyName, setCompanyName] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files?.[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.match(/\.(xlsx|xls)$/)) {
        setFile(droppedFile);
        setError(null);
      } else {
        setError('Excel files only (.xlsx or .xls)');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file || !companyName.trim()) {
      setError('Company name and file required');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('company_name', companyName.trim());

    try {
      const response = await fetch('/api/secure20/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (result?.download_url) window.open(result.download_url, '_blank');
  };

  const handleReset = () => {
    setFile(null);
    setCompanyName('');
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950">
      <div className="border-b border-cyan-500/20 bg-slate-900/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <TrendingUp className="w-6 h-6 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">SECURE 2.0 Analysis</h1>
              <p className="text-sm text-slate-400">ROTH Catch-up Compliance Engine</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-10">
        {!result ? (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2 tracking-wide">COMPANY NAME</label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Meyer Company"
                className="w-full px-5 py-3.5 bg-slate-900/60 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
              />
            </div>

            <div
              className={`relative border-2 border-dashed rounded-2xl p-16 transition-all cursor-pointer ${
                dragActive ? 'border-cyan-400 bg-cyan-500/10' : 'border-slate-700/50 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-900/60'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-upload')?.click()}
            >
              <input type="file" accept=".xlsx,.xls" onChange={handleFileChange} className="hidden" id="file-upload" />
              <div className="text-center">
                {file ? (
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-cyan-600 flex items-center justify-center shadow-xl shadow-cyan-500/30">
                      <FileSpreadsheet className="w-8 h-8 text-white" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-white">{file.name}</p>
                      <p className="text-sm text-slate-400 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); setFile(null); }} className="text-sm text-slate-400 hover:text-white transition-colors">
                      Remove file
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-slate-800/60 flex items-center justify-center border border-slate-700/50">
                      <Upload className="w-8 h-8 text-slate-500" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-white">Drop Excel file here</p>
                      <p className="text-sm text-slate-400 mt-1">or click to browse</p>
                    </div>
                    <p className="text-xs text-slate-500">5 tabs required: Wages, Earnings, Deductions, Employee Deductions, Employee Earnings</p>
                  </div>
                )}
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={loading || !file || !companyName.trim()}
              className="w-full py-4 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 disabled:from-slate-700 disabled:to-slate-700 text-white font-semibold rounded-xl transition-all shadow-lg shadow-cyan-500/30 disabled:shadow-none flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <TrendingUp className="w-5 h-5" />
                  Run Analysis
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center gap-3 p-4 bg-cyan-500/10 border border-cyan-500/30 rounded-xl">
              <CheckCircle className="w-6 h-6 text-cyan-400" />
              <div>
                <p className="text-lg font-semibold text-white">{result.message}</p>
                <p className="text-sm text-slate-400 mt-0.5">{result.company}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-6 bg-slate-900/60 border border-slate-700/50 rounded-xl">
                <p className="text-sm text-slate-400 mb-1">Total Employees</p>
                <p className="text-3xl font-bold text-white">{result.statistics.total_employees.toLocaleString()}</p>
              </div>
              <div className="p-6 bg-slate-900/60 border border-slate-700/50 rounded-xl">
                <p className="text-sm text-slate-400 mb-1">RCR Employees</p>
                <p className="text-3xl font-bold text-cyan-400">{result.statistics.rcr_employees}</p>
              </div>
              <div className="p-6 bg-red-500/10 border border-red-500/30 rounded-xl">
                <p className="text-sm text-red-300 mb-1">HIGH Priority</p>
                <p className="text-3xl font-bold text-red-400">{result.statistics.high_priority}</p>
                <p className="text-xs text-red-300/70 mt-2">Need ROTH codes</p>
              </div>
              <div className="p-6 bg-slate-900/60 border border-slate-700/50 rounded-xl">
                <p className="text-sm text-slate-400 mb-1">Monitor</p>
                <p className="text-3xl font-bold text-slate-300">{result.statistics.monitor}</p>
                <p className="text-xs text-slate-500 mt-2">No 401k participation</p>
              </div>
              <div className="col-span-2 p-6 bg-slate-900/60 border border-slate-700/50 rounded-xl">
                <p className="text-sm text-slate-400 mb-1">Average RCR Wages</p>
                <p className="text-3xl font-bold text-white">${result.statistics.avg_rcr_wages.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={handleDownload} className="flex-1 py-4 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-white font-semibold rounded-xl transition-all shadow-lg shadow-cyan-500/30 flex items-center justify-center gap-2">
                <Download className="w-5 h-5" />Download Report
              </button>
              <button onClick={handleReset} className="px-6 py-4 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 text-white font-semibold rounded-xl transition-all">
                New Analysis
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
