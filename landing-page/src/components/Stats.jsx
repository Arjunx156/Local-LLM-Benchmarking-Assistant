import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

const Counter = ({ end, suffix = '' }) => {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = 0; const dur = 2000; const inc = end / (dur / 16);
    const t = setInterval(() => { start += inc; if (start >= end) { setVal(end); clearInterval(t); } else setVal(Math.floor(start)); }, 16);
    return () => clearInterval(t);
  }, [end]);
  return <>{val}{suffix}</>;
};

export const Stats = ({ fade, modelCount }) => (
  <motion.section className="stats-bar" {...fade}>
    <div className="container">
      <div className="stats-grid">
        <div className="stat-item"><div className="stat-number"><Counter end={100} suffix="%" /></div><div className="stat-label">Offline & Private</div></div>
        <div className="stat-item"><div className="stat-number"><Counter end={3} /></div><div className="stat-label">Eval Strategies</div></div>
        <div className="stat-item"><div className="stat-number"><Counter end={500} suffix="ms" /></div><div className="stat-label">Metric Polling</div></div>
        <div className="stat-item"><div className="stat-number"><Counter end={modelCount} /></div><div className="stat-label">Models Installed</div></div>
      </div>
    </div>
  </motion.section>
);
