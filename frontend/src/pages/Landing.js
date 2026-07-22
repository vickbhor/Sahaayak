import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Languages, Gauge, Stethoscope, MapPin, ArrowRight, ChevronDown, ShieldAlert } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import Logo from '../components/Logo';
import TriageDemoPanel from '../components/TriageDemoPanel';

function Landing() {
  const { token, user } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in-view');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="landing-page">
      <nav className="landing-nav">
        <div className="landing-nav-brand">
          <Logo size={32} />
          <span>{t('brand_name')}</span>
        </div>
        <div className="landing-nav-actions">
          {token ? (
            <button className="landing-btn-primary" onClick={() => navigate('/dashboard')}>
              {t('nav_dashboard')} <ArrowRight size={15} />
            </button>
          ) : (
            <>
              <Link to="/login" className="landing-btn-ghost">{t('sign_in')}</Link>
              <Link to="/signup" className="landing-btn-primary">{t('create_account_btn')}</Link>
            </>
          )}
        </div>
      </nav>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <span className="landing-eyebrow">AI-POWERED HEALTHCARE TRIAGE</span>
          <h1>
            Describe how you feel.
            <br />
            <span className="landing-hero-accent">In your own words.</span>
          </h1>
          <p className="landing-hero-sub">
            Dr. Sahaayak follows Hindi, English, and the Hinglish in between. Talk
            naturally, and get triaged, matched to the right specialist, and pointed
            to nearby care, without ever needing to translate yourself first.
          </p>
          <div className="landing-hero-actions">
            {user ? (
              <button className="landing-btn-primary large" onClick={() => navigate('/dashboard')}>
                {t('nav_dashboard')} <ArrowRight size={17} />
              </button>
            ) : (
              <button className="landing-btn-primary large" onClick={() => navigate('/signup')}>
                Get Started <ArrowRight size={17} />
              </button>
            )}
            <a href="#how-it-works" className="landing-btn-text">
              See how it works <ChevronDown size={15} />
            </a>
          </div>
        </div>
        <div className="landing-hero-visual">
          <TriageDemoPanel />
        </div>
      </section>

      <section className="landing-features reveal">
        <div className="landing-section-head">
          <h2>Built for the way people actually describe symptoms</h2>
        </div>
        <div className="landing-features-grid">
          <div className="landing-feature-card">
            <div className="landing-feature-icon"><Languages size={22} /></div>
            <h3>Understands you, in your language</h3>
            <p>Speak in Hindi, English, or a natural mix of both. Dr. Sahaayak is built to follow along either way.</p>
          </div>
          <div className="landing-feature-card">
            <div className="landing-feature-icon"><Gauge size={22} /></div>
            <h3>Instant urgency triage</h3>
            <p>Every conversation ends with a clear Low, Medium, High, or Critical read on how urgent things are.</p>
          </div>
          <div className="landing-feature-card">
            <div className="landing-feature-icon"><Stethoscope size={22} /></div>
            <h3>The right specialist, first try</h3>
            <p>Get pointed to the specialist your symptoms actually call for, not a generic checkup.</p>
          </div>
          <div className="landing-feature-card">
            <div className="landing-feature-icon"><MapPin size={22} /></div>
            <h3>Care close to home</h3>
            <p>When it matters, find the nearest hospital or clinic and its phone number in seconds.</p>
          </div>
        </div>
      </section>

      <section className="landing-how" id="how-it-works">
        <div className="landing-section-head reveal">
          <h2>From symptom to next step, in three parts</h2>
        </div>
        <div className="landing-steps">
          <div className="landing-step reveal">
            <span className="landing-step-num">01</span>
            <h3>Describe your symptoms</h3>
            <p>Talk to Dr. Sahaayak like you would a helpful neighbour who happens to know medicine.</p>
          </div>
          <div className="landing-step reveal">
            <span className="landing-step-num">02</span>
            <h3>Get assessed</h3>
            <p>Your symptoms are matched against a trained model and turned into a clear report — urgency, likely condition, and recommended specialist.</p>
          </div>
          <div className="landing-step reveal">
            <span className="landing-step-num">03</span>
            <h3>Find the right care</h3>
            <p>High-risk cases are flagged immediately. Every report is saved, and nearby hospitals are one tap away.</p>
          </div>
        </div>
      </section>

      <section className="landing-cta-band reveal">
        <ShieldAlert size={28} />
        <h2>Your symptoms deserve a fast, clear answer.</h2>
        {user ? (
          <button className="landing-btn-dark" onClick={() => navigate('/dashboard')}>{t('nav_dashboard')}</button>
        ) : (
          <button className="landing-btn-dark" onClick={() => navigate('/signup')}>Create your account</button>
        )}
      </section>

      <footer className="landing-footer">
        <div className="landing-footer-brand">
          <Logo size={26} />
          <span>{t('brand_name')}</span>
        </div>
        <p className="landing-footer-tagline">AI-assisted triage for every corner of India.</p>
        <p className="landing-footer-disclaimer">
          Dr. Sahaayak offers AI-assisted guidance and does not replace professional medical
          diagnosis. In a medical emergency, contact your local emergency services immediately.
        </p>
      </footer>
    </div>
  );
}

export default Landing;
