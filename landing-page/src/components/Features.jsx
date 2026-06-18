import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Lock, Zap, BarChart3, Download, Cpu } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';

export const Features = ({ fade }) => (
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
);
