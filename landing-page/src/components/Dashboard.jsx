import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Database, Play, Lock, Download, Activity } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

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
  const pollRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, m, su] = await Promise.all([fetch(`${API}/system`), fetch(`${API}/models`), fetch(`${API}/suites`)]);
        if (s.ok) setSysInfo(await s.json());
        if (m.ok) { const d = await m.json(); setModels(d.models || []); if (d.models?.length) setSelModel(d.models[0].name); }
        if (su.ok) { const d = await su.json(); setSuites(d.suites || []); if (d.suites?.length) setSelSuite(d.suites[0]); }
      } catch (e) { console.error(e); }
    })();
  }, [API]);

  useEffect(() => {
    if (!jobId || !['running', 'queued'].includes(jobStatus)) return;
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/benchmark/${jobId}/poll`);
        if (!r.ok) return;
        const d = await r.json();
        setJobData(d); setJobStatus(d.status);
        if (d.results?.length) {
          const l = d.results[d.results.length - 1];
          setChartData(p => [...p.slice(-19), { t: new Date().toLocaleTimeString('en-US', { hour12: false }), tok: l.tokens_per_second || 0, ram: l.peak_ram_mb ? l.peak_ram_mb / 1024 : 0 }]);
        }
        if (['done', 'cancelled', 'error'].includes(d.status)) clearInterval(pollRef.current);
      } catch (e) { console.error(e); }
    }, 1000);
    return () => clearInterval(pollRef.current);
  }, [jobId, jobStatus, API]);

  const run = async () => {
    if (!selModel || !selSuite) return;
    setChartData([]);
    try {
      const r = await fetch(`${API}/benchmark/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ models: [selModel], suite: selSuite }) });
      if (r.ok) { const d = await r.json(); setJobId(d.job_id); setJobStatus('queued'); setJobData(null); }
    } catch (e) { console.error(e); }
  };

  const abort = async () => { if (jobId) fetch(`${API}/benchmark/${jobId}/cancel`, { method: 'POST' }).catch(console.error); };
  const isRunning = ['running', 'queued'].includes(jobStatus);

  return (
    <motion.section id="dashboard" className="dashboard-section" {...fade}>
      <div className="container">
        <div className="section-label">Live Dashboard</div>
        <h2 className="section-title">Mission Control.</h2>
        <p className="section-subtitle">Select a model, pick a suite, and watch the telemetry unfold in real-time.</p>

        <div className="dashboard-grid">
          <div className="control-panel">
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}><Database size={16} style={{ display: 'inline', marginRight: 8 }} />Parameters</h3>
            <div><label>Target Model</label><select value={selModel} onChange={e => setSelModel(e.target.value)} disabled={isRunning}>{models.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}</select></div>
            <div><label>Eval Suite</label><select value={selSuite} onChange={e => setSelSuite(e.target.value)} disabled={isRunning}>{suites.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}</select></div>
            
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.5rem', marginTop: '0.5rem' }}>
              <label>System Status</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Ollama</span><span style={{ color: sysInfo?.ollama_running ? '#22c55e' : '#f43f5e' }}>{sysInfo?.ollama_running ? '● Online' : '● Offline'}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>RAM</span><span>{sysInfo?.ram_total_gb?.toFixed(1) || '—'} GB</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>CPU Cores</span><span>{sysInfo?.cpu_count_logical || '—'}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>GPU</span><span>{sysInfo?.gpu_name || 'N/A'}</span></div>
              </div>
            </div>

            {!isRunning
              ? <button className="btn-execute" onClick={run}><Play size={16} /> Execute Benchmark</button>
              : <button className="btn-abort" onClick={abort}><Lock size={16} /> Abort Sequence</button>
            }

            {jobStatus === 'done' && jobId && (
              <a href={`${API}/reports/${jobId}/excel`} style={{ textDecoration: 'none' }}><button className="btn-execute" style={{ background: 'linear-gradient(135deg, #22c55e 0%, #10b981 100%)' }}><Download size={16} /> Download Report</button></a>
            )}
          </div>

          <div className="charts-panel">
            <div className="charts-panel-header">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}><Activity size={16} style={{ display: 'inline', marginRight: 8 }} />Live Telemetry</h3>
              <span className="mono" style={{ fontSize: '0.75rem', color: isRunning ? '#00d4ff' : 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 2 }}>{jobStatus}</span>
            </div>
            <div className="charts-grid">
              <div className="chart-box">
                <div className="chart-label">Tokens / Second</div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={chartData}><defs><linearGradient id="ct" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#00d4ff" stopOpacity={0.7}/><stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" /><XAxis dataKey="t" stroke="#333" fontSize={10} /><YAxis stroke="#333" fontSize={10} /><Tooltip contentStyle={{ background: '#111', border: '1px solid #222' }} /><Area type="monotone" dataKey="tok" stroke="#00d4ff" fill="url(#ct)" isAnimationActive={false} /></AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="chart-box">
                <div className="chart-label">Memory Overhead (GB)</div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={chartData}><defs><linearGradient id="cr" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f43f5e" stopOpacity={0.7}/><stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" /><XAxis dataKey="t" stroke="#333" fontSize={10} /><YAxis stroke="#333" fontSize={10} /><Tooltip contentStyle={{ background: '#111', border: '1px solid #222' }} /><Area type="monotone" dataKey="ram" stroke="#f43f5e" fill="url(#cr)" isAnimationActive={false} /></AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.section>
  );
};
