import React from 'react';
import { Zap } from 'lucide-react';

export const Navbar = ({ scrolled }) => (
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
);
