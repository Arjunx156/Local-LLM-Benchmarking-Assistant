import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Minus, Zap, ArrowRight } from 'lucide-react';

const FaqItem = ({ q, a }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="faq-item" onClick={() => setOpen(!open)}>
      <div className="faq-question">{q} {open ? <Minus size={20} /> : <Plus size={20} />}</div>
      {open && <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="faq-answer">{a}</motion.div>}
    </div>
  );
};

export const FAQ = ({ fade }) => (
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
);

export const CTA = () => (
  <section className="cta-section">
    <div className="cta-glow" />
    <div className="container" style={{ position: 'relative', zIndex: 2 }}>
      <h2 className="section-title">Ready to benchmark<br/><span style={{ background: 'var(--gradient-1)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>your models?</span></h2>
      <p className="section-subtitle" style={{ margin: '2rem auto' }}>Get started in under 60 seconds. No sign-up, no API keys, no cloud dependencies.</p>
      <a href="#dashboard"><button className="btn-primary" style={{ fontSize: '1.1rem', padding: '1.25rem 3rem' }}><Zap size={20} /> Launch Dashboard <ArrowRight size={20} /></button></a>
    </div>
  </section>
);

export const Footer = () => (
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
);
