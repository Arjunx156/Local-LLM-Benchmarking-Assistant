import React from 'react';
import { motion } from 'framer-motion';
import { Play, Terminal } from 'lucide-react';

export const Hero = () => (
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
);
