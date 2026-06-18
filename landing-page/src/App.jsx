import React, { useEffect, useState } from 'react';
import { Background3D } from './components/Background3D';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { Stats } from './components/Stats';
import { Features } from './components/Features';
import { HowItWorks, TerminalBlock, ComparisonTable } from './components/MiddleSections';
import { Dashboard } from './components/Dashboard';
import { FAQ, CTA, Footer } from './components/FooterSections';
import './index.css';

// When deployed to Vercel, requests go through /api proxy (vercel.json rewrites)
// When running locally, fall back to direct localhost
const IS_PROD = import.meta.env.PROD;
const API = IS_PROD ? '' : (import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000');
const API_PREFIX = IS_PROD ? '/api' : API;

export default function App() {
  const [scrolled, setScrolled] = useState(false);
  const [modelCount, setModelCount] = useState(0);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => { 
    const h = () => setScrolled(window.scrollY > 50); 
    window.addEventListener('scroll', h); 
    return () => window.removeEventListener('scroll', h); 
  }, []);

  useEffect(() => {
    fetch(`${API_PREFIX}/models`)
      .then(r => r.json())
      .then(d => setModelCount(d.models?.length || 0))
      .catch(console.error);
  }, []);

  const fade = { 
    initial: { opacity: 0, y: 40 }, 
    whileInView: { opacity: 1, y: 0 }, 
    viewport: { once: true, amount: 0.2 }, 
    transition: { duration: 0.7 } 
  };

  return (
    <>
      <Background3D isRunning={isRunning} />
      <Navbar scrolled={scrolled} />
      
      <Hero />

      <div style={{ overflow: 'hidden', padding: '3rem 0', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <div className="marquee-track">
          {['OLLAMA', 'FASTAPI', 'ASYNC', 'PRIVACY', 'METRICS', 'REPORTS', 'EVALUATION', 'LOCAL-FIRST', 'OLLAMA', 'FASTAPI', 'ASYNC', 'PRIVACY', 'METRICS', 'REPORTS', 'EVALUATION', 'LOCAL-FIRST'].map((t, i) => <span key={i} className="marquee-item">{t}</span>)}
        </div>
      </div>

      <Stats fade={fade} modelCount={modelCount} />
      <Features fade={fade} />
      <HowItWorks fade={fade} />
      <TerminalBlock fade={fade} />
      <Dashboard fade={fade} API={API_PREFIX} />
      <ComparisonTable fade={fade} />
      <FAQ fade={fade} />
      <CTA />
      <Footer />
    </>
  );
}
