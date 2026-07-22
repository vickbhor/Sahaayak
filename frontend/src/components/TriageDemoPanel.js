import React, { useState, useEffect, useRef } from 'react';
import { Sparkles } from 'lucide-react';

const examples = [
  { text: 'मुझे 3 दिन से तेज़ बुखार और सिर दर्द है...', urgency: 'HIGH', specialist: 'General Physician', tag: 'हिंदी' },
  { text: 'Mera chest mein tightness hai aur saans phoolti hai...', urgency: 'CRITICAL', specialist: 'Cardiologist', tag: 'Hinglish' },
  { text: 'I have had a mild dry cough for about a week now...', urgency: 'LOW', specialist: 'General Physician', tag: 'English' }
];

function TriageDemoPanel() {
  const [index, setIndex] = useState(0);
  const [displayed, setDisplayed] = useState('');
  const [phase, setPhase] = useState('typing');
  const reducedMotion = useRef(
    typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  useEffect(() => {
    if (reducedMotion.current) {
      setDisplayed(examples[0].text);
      setPhase('result');
      return undefined;
    }

    let charTimer;
    let phaseTimer;
    const current = examples[index];

    if (phase === 'typing') {
      let i = 0;
      charTimer = setInterval(() => {
        i += 1;
        setDisplayed(current.text.slice(0, i));
        if (i >= current.text.length) {
          clearInterval(charTimer);
          phaseTimer = setTimeout(() => setPhase('assessing'), 450);
        }
      }, 28);
    } else if (phase === 'assessing') {
      phaseTimer = setTimeout(() => setPhase('result'), 900);
    } else if (phase === 'result') {
      phaseTimer = setTimeout(() => {
        setDisplayed('');
        setIndex((prev) => (prev + 1) % examples.length);
        setPhase('typing');
      }, 2700);
    }

    return () => {
      clearInterval(charTimer);
      clearTimeout(phaseTimer);
    };
  }, [phase, index]);

  const current = examples[index];

  return (
    <div className="demo-panel">
      <div className="demo-panel-head">
        <Sparkles size={13} /> Live example <span className="demo-lang-tag">{current.tag}</span>
      </div>
      <div className="demo-bubble">
        {displayed}
        {phase === 'typing' && <span className="demo-cursor">|</span>}
      </div>
      <div className={`demo-result-row ${phase !== 'typing' ? 'show' : ''}`}>
        {phase === 'assessing' && (
          <div className="demo-assessing">
            Assessing
            <span className="demo-dots"><span>.</span><span>.</span><span>.</span></span>
          </div>
        )}
        {phase === 'result' && (
          <>
            <span className="urgency-badge small" data-urgency={current.urgency}>{current.urgency}</span>
            <span className="demo-specialist-chip">{current.specialist}</span>
          </>
        )}
      </div>
    </div>
  );
}

export default TriageDemoPanel;
