import { useState, useEffect } from 'react';
// 1. IMPORT deployModel HERE
import { api, deployModel } from './api'; 
import { Play, Code, CheckCircle, AlertCircle, RefreshCw, Terminal, Rocket } from 'lucide-react';

interface Job {
  id: number;
  status: string;
  argo_workflow_name: string;
  team_id: number;
}

interface Model {
  id: number;
  name: string;
  s3_path: string;
  created_at: string;
}

function App() {
  const [team, setTeam] = useState('omega'); 
  const [code, setCode] = useState("import os\nprint('Hello from UI')");
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  
  const [jobs, setJobs] = useState<Job[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  
  const [selectedLogs, setSelectedLogs] = useState<string>("");
  const [showLogs, setShowLogs] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [jobsRes, modelsRes] = await Promise.all([
        api.get('/jobs'),
        api.get('/models')
      ]);
      setJobs(jobsRes.data);
      setModels(modelsRes.data);
    } catch (e) { 
      console.error("Failed to load data"); 
    }
  };

  const handleSubmit = async () => {
    setStatus('loading');
    try {
      await api.post('/jobs', { team_name: team, python_code: code });
      setStatus('success');
      loadData();
    } catch (err) {
      setStatus('error');
    }
  };

  const viewLogs = async (jobId: number) => {
    setSelectedLogs("Loading logs from Kubernetes...");
    setShowLogs(true);
    try {
      const res = await api.get(`/jobs/${jobId}/logs`);
      setSelectedLogs(res.data.logs);
    } catch (e) {
      setSelectedLogs("Failed to fetch logs. Pod might be deleted.");
    }
  };

  // 2. NEW FUNCTION TO HANDLE DEPLOYMENT
  const handleDeploy = async (model: Model) => {
    if(!confirm(`Are you sure you want to deploy ${model.name}?`)) return;
    
    try {
      await deployModel(model.id);
      alert(`🚀 Deployment Triggered for ${model.name}!\n\nCheck Kubernetes using:\nkubectl get pods -n team-${team}`);
    } catch (e) {
      alert("Failed to deploy model. Check backend logs.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* SUBMISSION CARD */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <Code className="text-blue-600" /> ML Job Submission
          </h1>
          <div className="space-y-4">
            <input type="text" value={team} onChange={(e) => setTeam(e.target.value)} className="border p-2 rounded w-full" placeholder="Team Name"/>
            <textarea value={code} onChange={(e) => setCode(e.target.value)} rows={5} className="border p-2 rounded w-full font-mono bg-slate-900 text-green-400" />
            <button onClick={handleSubmit} disabled={status === 'loading'} className="bg-blue-600 text-white px-4 py-2 rounded flex items-center gap-2">
              {status === 'loading' ? 'Submitting...' : <><Play size={16}/> Run Job</>}
            </button>
          </div>
        </div>

        {/* JOB HISTORY CARD */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Job History</h2>
            <button onClick={loadData} className="text-gray-500 hover:text-blue-600"><RefreshCw size={20}/></button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="p-3">ID</th>
                  <th className="p-3">Workflow Name</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-b hover:bg-gray-50">
                    <td className="p-3">#{job.id}</td>
                    <td className="p-3 font-mono text-xs">{job.argo_workflow_name}</td>
                    <td className="p-3"><span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">Submitted</span></td>
                    <td className="p-3">
                      <button onClick={() => viewLogs(job.id)} className="text-sm border border-gray-300 px-3 py-1 rounded hover:bg-gray-100 flex items-center gap-2">
                        <Terminal size={14}/> Logs
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* MODEL REGISTRY CARD */}
        <div className="bg-white rounded-xl shadow-md p-6 mt-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <div className="w-3 h-3 bg-purple-500 rounded-full"></div> Model Registry
          </h2>
  
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map((model) => (
              <div key={model.id} className="border rounded-lg p-4 hover:shadow-lg transition bg-gray-50">
                <div className="flex justify-between items-start">
                  <h3 className="font-bold text-gray-800">{model.name}</h3>
                  <span className="text-xs bg-gray-200 px-2 py-1 rounded text-gray-600">v{model.id}</span>
                </div>
                <p className="text-xs text-gray-500 mt-2 font-mono break-all">{model.s3_path}</p>
                <div className="mt-4 flex gap-2">
                  
                  {/* 3. THIS IS THE REAL DEPLOY BUTTON */}
                  <button 
                    onClick={() => handleDeploy(model)}
                    className="text-xs bg-purple-600 text-white px-3 py-2 rounded hover:bg-purple-700 w-full flex items-center justify-center gap-2"
                  >
                    <Rocket size={14} /> Deploy API
                  </button>

                </div>
              </div>
            ))}
          </div>
        </div>

        {/* LOG VIEWER MODAL */}
        {showLogs && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4">
            <div className="bg-slate-900 text-white w-full max-w-3xl rounded-lg overflow-hidden shadow-2xl flex flex-col max-h-[80vh]">
              <div className="p-4 border-b border-slate-700 flex justify-between">
                <span className="font-mono font-bold">Job Logs</span>
                <button onClick={() => setShowLogs(false)} className="text-gray-400 hover:text-white">Close</button>
              </div>
              <div className="p-4 overflow-auto font-mono text-sm whitespace-pre-wrap">
                {selectedLogs}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default App;