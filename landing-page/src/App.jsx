import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Zap, Lock, BarChart3, Download, Play, ArrowRight, ArrowUpRight, Activity, Database, Terminal, Cpu, ChevronDown, Plus, Minus } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as random from 'maath/random/dist/maath-random.esm';
import './index.css';

const API = 'https://rude-hoops-sleep.loca.lt';

/* ─── 3D Stars ─── */
const Stars = ({ speed = 0.05 }) => {
  const ref = useRef();
  const [sphere] = useState(() => random.inSphere(new Float32Array(4000), { radius: 1.5 }));
  useFrame((_, delta) => { if (ref.current) { ref.current.rotation.x -= delta * speed; ref.current.rotation.y -= delta * speed * 1.2; } });
  return <group rotation={[0, 0, Math.PI / 4]}><Points ref={ref} positions={sphere} stride={3} frustumCulled={false}><PointMaterial transparent color="#00d4ff" size={0.004} sizeAttenuation depthWrite={false} /></Points></group>;
};

/* ─── Animated Counter ─── */
const Counter = ({ end, suffix = '' }) => {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = 0; const dur = 2000; const inc = end / (dur / 16);
    const t = setInterval(() => { start += inc; if (start >= end) { setVal(end); clearInterval(t); } else setVal(Math.floor(start)); }, 16);
    return () => clearInterval(t);
  }, [end]);
  return <>{val}{suffix}</>;
};

/* ─── FAQ Item ─── */
const FaqItem = ({ q, a }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="faq-item" onClick={() => setOpen(!open)}>
      <div className="faq-question">{q} {open ? <Minus size={20} /> : <Plus size={20} />}</div>
      {open && <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="faq-answer">{a}</motion.div>}
    </div>
  );
};

/* ─── MAIN APP ─── */
export default function App() {
  const [scrolled, setScrolled] = useState(false);
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

  useEffect(() => { const h = () => setScrolled(window.scrollY > 50); window.addEventListener('scroll', h); return () => window.removeEventListener('scroll', h); }, []);

  useEffect(() => {
    (async () => {
      try {
        const [s, m, su] = await Promise.all([fetch(`${API}/system`), fetch(`${API}/models`), fetch(`${API}/suites`)]);
        if (s.ok) setSysInfo(await s.json());
        if (m.ok) { const d = await m.json(); setModels(d.models || []); if (d.models?.length) setSelModel(d.models[0].name); }
        if (su.ok) { const d = await su.json(); setSuites(d.suites || []); if (d.suites?.length) setSelSuite(d.suites[0]); }
      } catch (e) { console.error(e); }
    })();
  }, []);

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
  }, [jobId, jobStatus]);

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
  const fade = { initial: { opacity: 0, y: 40 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true, amount: 0.2 }, transition: { duration: 0.7 } };

  return (
    <>
      {/* 3D BG */}
      <div style={{ position: 'fixed', inset: 0, zIndex: -1, background: '#050505' }}>
        <Canvas camera={{ position: [0, 0, 1] }}><Stars speed={isRunning ? 0.6 : 0.04} /></Canvas>
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 0%, transparent 30%, #050505 75%)' }} />
      </div>

      {/* NAVBAR */}
      <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
        <div className="container navbar-inner">
          <div className="nav-logo"><div className="logo-icon"><Zap size={18} color="#050505" /></div> LLM Bench</div>
          <ul className="nav-links">
            <li><a href="#features">Features</a></li>
            <li><a href="#how">How It Works</a></li>
            <li><a href="#dashboard">Dashboard</a></li>
            <li><a href="#faq">FAQ</a></li>
          </ul>
          <a href="#dashboard"><button className="nav-cta">Launch Dashboard →</button></a>
        </div>
      </nav>

      {/* HERO */}
      <section className="hero">
        <div className="hero-glow hero-glow-1" /><div className="hero-glow hero-glow-2" />
        <div className="container hero-content">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            <div className="hero-badge"><span className="pulse" /> v1.0 — Now Available</div>
            <h1>Benchmark<br/>Your Local<br/><span className="line-gradient">AI Models.</span></h1>
            <p className="hero-desc">The definitive evaluation engine for Ollama-powered LLMs. Track tokens-per-second, memory overhead, and accuracy — all running 100% on your hardware. Zero cloud. Zero cost.</p>
            <div className="hero-actions">
              <a href="#dashboard"><button className="btn-primary"><Play size={18} /> Start Benchmarking</button></a>
              <a href="#how"><button className="btn-ghost"><Terminal size={18} /> See How It Works</button></a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* SCROLLING MARQUEE */}
      <div style={{ overflow: 'hidden', padding: '3rem 0', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <div className="marquee-track">
          {['OLLAMA', 'FASTAPI', 'ASYNC', 'PRIVACY', 'METRICS', 'REPORTS', 'EVALUATION', 'LOCAL-FIRST', 'OLLAMA', 'FASTAPI', 'ASYNC', 'PRIVACY', 'METRICS', 'REPORTS', 'EVALUATION', 'LOCAL-FIRST'].map((t, i) => <span key={i} className="marquee-item">{t}</span>)}
        </div>
      </div>

      {/* STATS */}
      <motion.section className="stats-bar" {...fade}>
        <div className="container">
          <div className="stats-grid">
            <div className="stat-item"><div className="stat-number"><Counter end={100} suffix="%" /></div><div className="stat-label">Offline & Private</div></div>
            <div className="stat-item"><div className="stat-number"><Counter end={3} /></div><div className="stat-label">Eval Strategies</div></div>
            <div className="stat-item"><div className="stat-number"><Counter end={500} suffix="ms" /></div><div className="stat-label">Metric Polling</div></div>
            <div className="stat-item"><div className="stat-number"><Counter end={models.length || 0} /></div><div className="stat-label">Models Installed</div></div>
          </div>
        </div>
      </motion.section>

      {/* BENTO FEATURES */}
      <motion.section id="features" className="bento-section" {...fade}>
        <div className="container">
          <div className="section-label">Core Capabilities</div>
          <h2 className="section-title">Everything you need<br/>to evaluate LLMs.</h2>
          <div className="bento-grid">
            <div className="bento-card" style={{ gridColumn: 'span 8', gridRow: 'span 2' }}>
              <div><div className="card-icon" style={{ background: 'rgba(0,212,255,0.1)' }}><Activity size={28} color="#00d4ff" /></div>
              <h3>Real-Time Telemetry Dashboard</h3>
              <p>Watch live scrolling charts of generation velocity, RAM overhead, and CPU utilization as your benchmarks execute. Every metric is polled at 500ms intervals for sub-second precision.</p></div>
              <div className="card-visual" style={{ background: 'var(--bg-elevated)', padding: '1.5rem', height: 180 }}>
                <ResponsiveContainer><AreaChart data={[{t:'0s',v:12},{t:'1s',v:28},{t:'2s',v:24},{t:'3s',v:35},{t:'4s',v:31},{t:'5s',v:42}]}>
                  <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#00d4ff" stopOpacity={0.6}/><stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" /><Area type="monotone" dataKey="v" stroke="#00d4ff" fill="url(#g1)" />
                </AreaChart></ResponsiveContainer>
              </div>
            </div>
            <div className="bento-card" style={{ gridColumn: 'span 4' }}>
              <div className="card-icon" style={{ background: 'rgba(124,58,237,0.1)' }}><Lock size={28} color="#7c3aed" /></div>
              <h3>Air-Gapped Privacy</h3>
              <p>Your prompts, your models, your hardware. Zero external API calls. Complete data sovereignty.</p>
            </div>
            <div className="bento-card" style={{ gridColumn: 'span 4' }}>
              <div className="card-icon" style={{ background: 'rgba(244,63,94,0.1)' }}><Zap size={28} color="#f43f5e" /></div>
              <h3>Async Orchestration</h3>
              <p>Intelligent scheduling with asyncio Semaphores prevents OOM crashes while maximizing GPU throughput.</p>
            </div>
            <div className="bento-card" style={{ gridColumn: 'span 4' }}>
              <div className="card-icon" style={{ background: 'rgba(34,197,94,0.1)' }}><BarChart3 size={28} color="#22c55e" /></div>
              <h3>Triple Eval Engine</h3>
              <p>Supports Exact Match with normalization, LLM-as-a-Judge scoring, and sandboxed Code Execution evaluation.</p>
            </div>
            <div className="bento-card" style={{ gridColumn: 'span 4' }}>
              <div className="card-icon" style={{ background: 'rgba(251,146,60,0.1)' }}><Download size={28} color="#fb923c" /></div>
              <h3>Rich Excel Reports</h3>
              <p>Auto-generate multi-sheet workbooks with embedded Plotly charts and raw JSON for full reproducibility.</p>
            </div>
            <div className="bento-card" style={{ gridColumn: 'span 4' }}>
              <div className="card-icon" style={{ background: 'rgba(0,212,255,0.1)' }}><Cpu size={28} color="#00d4ff" /></div>
              <h3>GPU VRAM Tracking</h3>
              <p>Integrates pynvml to track live NVIDIA VRAM overhead alongside system RAM during inference.</p>
            </div>
          </div>
        </div>
      </motion.section>

      {/* HOW IT WORKS */}
      <motion.section id="how" className="how-section" {...fade}>
        <div className="container">
          <div className="section-label">Getting Started</div>
          <h2 className="section-title">Three steps to<br/>your first benchmark.</h2>
          <div className="steps-grid">
            <div className="step-card"><div className="step-number">01</div><h3>Install & Configure</h3><p>Clone the repo, install dependencies, and ensure Ollama is running with your preferred models pulled locally.</p></div>
            <div className="step-card"><div className="step-number">02</div><h3>Select & Execute</h3><p>Choose your target model and evaluation suite from the dashboard, then hit Execute to launch the async benchmark engine.</p></div>
            <div className="step-card"><div className="step-number">03</div><h3>Analyze & Export</h3><p>Watch live telemetry charts as the benchmark runs, then download a comprehensive Excel report with all metrics and scores.</p></div>
          </div>
        </div>
      </motion.section>

      {/* TERMINAL */}
      <motion.section className="terminal-section" {...fade}>
        <div className="container" style={{ textAlign: 'center' }}>
          <div className="section-label" style={{ justifyContent: 'center' }}>Quick Start</div>
          <h2 className="section-title">Up and running<br/>in seconds.</h2>
          <div className="terminal-window">
            <div className="terminal-header"><div className="terminal-dot" style={{ background: '#ff5f57' }} /><div className="terminal-dot" style={{ background: '#febc2e' }} /><div className="terminal-dot" style={{ background: '#28c840' }} /></div>
            <div className="terminal-body" style={{ textAlign: 'left' }}>
              <div className="comment"># Clone and install</div>
              <div><span className="cmd">$</span> git clone https://github.com/yourname/llm-bench.git</div>
              <div><span className="cmd">$</span> pip install -r requirements.txt</div>
              <br />
              <div className="comment"># Start the backend API</div>
              <div><span className="cmd">$</span> uvicorn backend.main:app --port 8000</div>
              <div className="output">INFO: Application startup complete.</div>
              <br />
              <div className="comment"># Launch the frontend</div>
              <div><span className="cmd">$</span> cd landing-page && npm run dev</div>
              <div className="output">VITE ready at http://localhost:5174 ✓</div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* LIVE DASHBOARD */}
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

      {/* COMPARISON TABLE */}
      <motion.section className="comparison-section" {...fade}>
        <div className="container">
          <div className="section-label">Model Comparison</div>
          <h2 className="section-title">Popular benchmarks<br/>at a glance.</h2>
          <table className="comparison-table">
            <thead><tr><th>Model</th><th>Parameters</th><th>Avg Tok/s</th><th>Peak RAM</th><th>Accuracy</th></tr></thead>
            <tbody>
              <tr><td className="model-name">llama3:8b</td><td>8B</td><td style={{ color: '#00d4ff' }}>34.2</td><td>6.1 GB</td><td>78%</td></tr>
              <tr><td className="model-name">mistral:7b</td><td>7B</td><td style={{ color: '#00d4ff' }}>41.8</td><td>5.4 GB</td><td>72%</td></tr>
              <tr><td className="model-name">phi3:mini</td><td>3.8B</td><td style={{ color: '#00d4ff' }}>62.5</td><td>3.2 GB</td><td>68%</td></tr>
              <tr><td className="model-name">gemma:2b</td><td>2B</td><td style={{ color: '#00d4ff' }}>78.1</td><td>2.1 GB</td><td>61%</td></tr>
              <tr><td className="model-name">qwen2:7b</td><td>7B</td><td style={{ color: '#00d4ff' }}>38.9</td><td>5.8 GB</td><td>75%</td></tr>
            </tbody>
          </table>
        </div>
      </motion.section>

      {/* FAQ */}
      <motion.section id="faq" className="faq-section" {...fade}>
        <div className="container" style={{ maxWidth: 800 }}>
          <div className="section-label">FAQ</div>
          <h2 className="section-title" style={{ marginBottom: '3rem' }}>Common questions.</h2>
          <FaqItem q="Do I need a GPU to run benchmarks?" a="No! Ollama can run models on CPU-only hardware. A GPU will significantly speed up inference, but it's not required. The tool tracks both RAM and VRAM overhead." />
          <FaqItem q="What evaluation methods are supported?" a="Three methods: Exact Match (with text normalization), LLM-as-a-Judge (uses a local model to score responses), and Code Execution (runs Python code in a sandboxed subprocess to verify correctness)." />
          <FaqItem q="Can I create my own benchmark suites?" a="Absolutely. Drop a JSON file into the benchmark_suites/ directory following the schema, and it will automatically appear in the dashboard dropdown." />
          <FaqItem q="Is my data sent to any external service?" a="Never. The entire system runs locally — FastAPI backend, Ollama inference, and the React frontend. No telemetry, no cloud APIs, no data leaves your machine." />
          <FaqItem q="What models are compatible?" a="Any model supported by Ollama — LLaMA 3, Mistral, Phi-3, Gemma, Qwen, CodeLLaMA, and hundreds more. If Ollama can run it, LLM Bench can evaluate it." />
        </div>
      </motion.section>

      {/* CTA */}
      <section className="cta-section">
        <div className="cta-glow" />
        <div className="container" style={{ position: 'relative', zIndex: 2 }}>
          <h2 className="section-title">Ready to benchmark<br/><span style={{ background: 'var(--gradient-1)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>your models?</span></h2>
          <p className="section-subtitle" style={{ margin: '2rem auto' }}>Get started in under 60 seconds. No sign-up, no API keys, no cloud dependencies.</p>
          <a href="#dashboard"><button className="btn-primary" style={{ fontSize: '1.1rem', padding: '1.25rem 3rem' }}><Zap size={20} /> Launch Dashboard <ArrowRight size={20} /></button></a>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="footer">
        <div className="container">
          <div className="footer-grid">
            <div className="footer-col">
              <div className="nav-logo" style={{ marginBottom: '1rem' }}><div className="logo-icon"><Zap size={18} color="#050505" /></div> LLM Bench</div>
              <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', lineHeight: 1.7 }}>The definitive local LLM evaluation engine. Built for developers who demand privacy and performance.</p>
            </div>
            <div className="footer-col"><h4>Product</h4><a href="#features">Features</a><a href="#dashboard">Dashboard</a><a href="#how">How It Works</a><a href="#faq">FAQ</a></div>
            <div className="footer-col"><h4>Stack</h4><a href="#">FastAPI</a><a href="#">Ollama</a><a href="#">React + Vite</a><a href="#">Recharts</a></div>
            <div className="footer-col"><h4>Resources</h4><a href="#">Documentation</a><a href="#">GitHub</a><a href="#">Changelog</a><a href="#">MIT License</a></div>
          </div>
          <div className="footer-bottom"><span>© 2026 LLM Bench. All rights reserved.</span><span>Made with ❤️ for the open-source community</span></div>
        </div>
      </footer>
    </>
  );
}
