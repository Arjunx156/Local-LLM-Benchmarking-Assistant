import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Database, Play, Lock, Download, Activity, Server, Cpu, Gpu, LayoutDashboard, History, Terminal } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import toast, { Toaster } from 'react-hot-toast';
import { supabase } from '../supabaseClient';

export const Dashboard = ({ fade, API }) => {
  const [sysInfo, setSysInfo] = useState(null);
  const [models, setModels] = useState([]);
  const [suites, setSuites] = useState([]);
  const [selModel, setSelModel] = useState('');
  const [selSuite, setSelSuite] = useState('');
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState('IDLE');
  const [jobData, setJobData] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [jobHistory, setJobHistory] = useState([]);
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('live'); // 'live' | 'history'
  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Fetch local system information and benchmark capabilities
  useEffect(() => {
    (async () => {
      try {
        const [s, m, su] = await Promise.all([fetch(`${API}/system`), fetch(`${API}/models`), fetch(`${API}/suites`)]);
        if (s.ok) setSysInfo(await s.json());
        if (m.ok) { const d = await m.json(); setModels(d.models || []); if (d.models?.length) setSelModel(d.models[0].name); }
        if (su.ok) { const d = await su.json(); setSuites(d.suites || []); if (d.suites?.length) setSelSuite(d.suites[0]); }
      } catch (e) { console.error("Could not fetch local node stats:", e); }
    })();
  }, [API]);

  // Fetch initial job history
  useEffect(() => {
    const fetchHistory = async () => {
      const { data, error } = await supabase.from('benchmark_jobs').select('*').order('created_at', { ascending: false }).limit(10);
      if (data) setJobHistory(data);
    };
    fetchHistory();
  }, []);

  // Subscribe to real-time job updates via Supabase
  useEffect(() => {
    if (!jobId || !['running', 'queued'].includes(jobStatus)) return;

    // Listen to changes on the current job
    const jobSub = supabase
      .channel(`job-${jobId}`)
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'benchmark_jobs', filter: `job_id=eq.${jobId}` }, (payload) => {
        const d = payload.new;
        setJobData(d);
        setJobStatus(d.status);
      })
      .subscribe();

    // Listen to new question results for real-time telemetry
    const resultsSub = supabase
      .channel(`results-${jobId}`)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'question_results', filter: `job_id=eq.${jobId}` }, (payload) => {
        const l = payload.new;
        const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
        setChartData(p => [...p.slice(-19), { 
          t: timeStr, 
          tok: l.tokens_per_second || 0, 
          ram: l.peak_ram_mb ? l.peak_ram_mb / 1024 : 0 
        }]);
        setLogs(p => [...p.slice(-49), {
          time: timeStr,
          msg: `Model: ${l.model_name} | Tokens/s: ${l.tokens_per_second?.toFixed(2)} | Latency: ${l.total_latency_seconds?.toFixed(2)}s | RAM: ${(l.peak_ram_mb/1024).toFixed(2)}GB`
        }]);
      })
      .subscribe();

    return () => {
      supabase.removeChannel(jobSub);
      supabase.removeChannel(resultsSub);
    };
  }, [jobId, jobStatus]);

  const run = async () => {
    if (!selModel || !selSuite) return;
    setChartData([]);
    setLogs([{ time: new Date().toLocaleTimeString('en-US', { hour12: false }), msg: 'Initializing benchmark sequence...' }]);
    const loadingToast = toast.loading('Starting benchmark...');
    try {
      // Trigger execution via local backend
      const r = await fetch(`${API}/benchmark/run`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ models: [selModel], suite: selSuite }) 
      });
      if (r.ok) { 
        const d = await r.json(); 
        setJobId(d.job_id); 
        setJobStatus('queued'); 
        setJobData(null); 
        setActiveTab('live');
        toast.success('Benchmark started!', { id: loadingToast });
      } else {
        toast.error('Failed to start benchmark.', { id: loadingToast });
      }
    } catch (e) { 
      console.error(e); 
      toast.error('Connection error. Is the local backend running?', { id: loadingToast });
    }
  };

  const abort = async () => { 
    if (jobId) {
      toast.promise(
        fetch(`${API}/benchmark/${jobId}/cancel`, { method: 'POST' }),
        { loading: 'Aborting...', success: 'Benchmark aborted.', error: 'Failed to abort.' }
      ).catch(console.error); 
    }
  };
  
  const isRunning = ['running', 'queued'].includes(jobStatus);
  const progressPercent = jobData?.progress?.overall_percent || 0;

  return (
    <motion.section id="dashboard" className="dashboard-section" {...fade}>
      <Toaster position="bottom-right" toastOptions={{ style: { background: 'var(--bg-elevated)', color: 'var(--text)', border: '1px solid var(--border)' } }} />
      <div className="container" style={{ maxWidth: '1200px' }}>
        <div className="section-label">Live Dashboard</div>
        <h2 className="section-title">Mission Control.</h2>
        <p className="section-subtitle">Orchestrate benchmarks and monitor global telemetry via Supabase Realtime.</p>

        <div className="dashboard-tabs">
          <button className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`} onClick={() => setActiveTab('live')}>
            <LayoutDashboard size={16} /> Live Execution
          </button>
          <button className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
            <History size={16} /> Job History
          </button>
        </div>

        {activeTab === 'live' ? (
          <div className="dashboard-grid glass-panel">
            <div className="control-panel">
              <h3 className="panel-heading"><Database size={18} /> Parameters</h3>
              <div className="input-group">
                <label>Target Model</label>
                <select className="glass-input" value={selModel} onChange={e => setSelModel(e.target.value)} disabled={isRunning}>
                  {models.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
                </select>
              </div>
              <div className="input-group">
                <label>Eval Suite</label>
                <select className="glass-input" value={selSuite} onChange={e => setSelSuite(e.target.value)} disabled={isRunning}>
                  {suites.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
                </select>
              </div>
              
              <div className="system-status-container">
                <h4 className="sub-heading">Node Capability Status</h4>
                <div className="sys-metrics">
                  <div className="sys-metric"><Server size={14} /> <span>Ollama</span> <span className={sysInfo?.ollama_running ? 'status-green' : 'status-red'}>{sysInfo?.ollama_running ? 'Online' : 'Offline'}</span></div>
                  <div className="sys-metric"><Database size={14} /> <span>RAM</span> <span>{sysInfo?.ram_total_gb?.toFixed(1) || '—'} GB</span></div>
                  <div className="sys-metric"><Cpu size={14} /> <span>CPU Cores</span> <span>{sysInfo?.cpu_count_logical || '—'}</span></div>
                </div>
              </div>

              {!isRunning
                ? <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="btn-execute" onClick={run}><Play size={16} /> Execute Benchmark</motion.button>
                : <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="btn-abort" onClick={abort}><Lock size={16} /> Abort Sequence</motion.button>
              }

              {jobStatus === 'done' && jobId && (
                <a href={`${API}/reports/${jobId}/excel`} style={{ textDecoration: 'none' }}>
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="btn-download">
                    <Download size={16} /> Download Report
                  </motion.button>
                </a>
              )}
            </div>

            <div className="charts-panel">
              <div className="charts-panel-header">
                <h3 className="panel-heading"><Activity size={18} /> Live Telemetry</h3>
                <div className="status-indicator">
                  <span className={`pulse-dot ${isRunning ? 'active' : ''}`}></span>
                  <span className="mono-status">{jobStatus}</span>
                </div>
              </div>

              {isRunning && (
                <div className="progress-container">
                  <div className="progress-bar-wrapper">
                    <motion.div className="progress-bar-fill" initial={{ width: 0 }} animate={{ width: `${progressPercent}%` }} transition={{ ease: 'linear', duration: 0.5 }}></motion.div>
                  </div>
                  <div className="progress-stats">
                    <span>{jobData?.progress?.current_model || 'Initializing...'}</span>
                    <span>{progressPercent.toFixed(1)}%</span>
                  </div>
                </div>
              )}

              <div className="charts-grid">
                <div className="chart-box">
                  <div className="chart-label">Tokens / Second</div>
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="ct" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.5}/>
                          <stop offset="95%" stopColor="#00e5ff" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                      <XAxis dataKey="t" stroke="#555" fontSize={10} tickLine={false} axisLine={false} />
                      <YAxis stroke="#555" fontSize={10} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ background: 'rgba(10, 10, 15, 0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', backdropFilter: 'blur(10px)' }} />
                      <Area type="monotone" dataKey="tok" stroke="#00e5ff" strokeWidth={2} fill="url(#ct)" isAnimationActive={true} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="chart-box">
                  <div className="chart-label">Memory Overhead (GB)</div>
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="cr" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ff007f" stopOpacity={0.5}/>
                          <stop offset="95%" stopColor="#ff007f" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                      <XAxis dataKey="t" stroke="#555" fontSize={10} tickLine={false} axisLine={false} />
                      <YAxis stroke="#555" fontSize={10} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ background: 'rgba(10, 10, 15, 0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', backdropFilter: 'blur(10px)' }} />
                      <Area type="monotone" dataKey="ram" stroke="#ff007f" strokeWidth={2} fill="url(#cr)" isAnimationActive={true} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
              
              <div className="terminal-log-box">
                <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-dim)', marginBottom: '8px', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
                  <Terminal size={14} /> Telemetry Stream
                </h4>
                {logs.length === 0 ? <p style={{ opacity: 0.5 }}>Waiting for telemetry data...</p> : null}
                {logs.map((log, i) => (
                  <p key={i}><span className="log-time">[{log.time}]</span> {log.msg}</p>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          </div>
        ) : (
          <div className="history-panel glass-panel">
            <h3 className="panel-heading"><History size={18} /> Recent Benchmark Runs</h3>
            <div className="table-responsive">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Suite</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobHistory.length === 0 ? (
                    <tr><td colSpan="4" style={{ textAlign: 'center', color: '#666', padding: '2rem' }}>No history found in Supabase.</td></tr>
                  ) : (
                    jobHistory.map(j => (
                      <tr key={j.job_id}>
                        <td>{new Date(j.created_at).toLocaleString()}</td>
                        <td><span className="badge-suite">{j.suite}</span></td>
                        <td><span className={`badge-status ${j.status}`}>{j.status}</span></td>
                        <td>
                          {j.status === 'done' ? (
                            <a href={`${API}/reports/${j.job_id}/excel`} className="text-link">Download</a>
                          ) : '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </motion.section>
  );
};
