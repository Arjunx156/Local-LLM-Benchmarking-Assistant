import React from 'react';
import { motion } from 'framer-motion';

export const HowItWorks = ({ fade }) => (
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
);

export const TerminalBlock = ({ fade }) => (
  <motion.section className="terminal-section" {...fade}>
    <div className="container" style={{ textAlign: 'center' }}>
      <div className="section-label" style={{ justifyContent: 'center' }}>Quick Start</div>
      <h2 className="section-title">Up and running<br/>in seconds.</h2>
      <div className="terminal-window">
        <div className="terminal-header"><div className="terminal-dot" style={{ background: '#ff5f57' }} /><div className="terminal-dot" style={{ background: '#febc2e' }} /><div className="terminal-dot" style={{ background: '#28c840' }} /></div>
        <div className="terminal-body" style={{ textAlign: 'left' }}>
          <div className="comment"># Clone and install</div>
          <div><span className="cmd">$</span> git clone https://github.com/Arjunx156/Local-LLM-Benchmarking-Assistant.git</div>
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
);

export const ComparisonTable = ({ fade }) => (
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
);
