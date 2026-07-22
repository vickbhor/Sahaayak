import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, LogIn, Languages, Gauge, MapPin } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import Logo from '../components/Logo';

function Login() {
  const { login } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-visual-panel">
        <div className="auth-visual-blob-1" />
        <div className="auth-visual-blob-2" />
        <div className="auth-visual-content">
          <Logo size={44} />
          <h2 className="auth-visual-brand">{t('brand_name')}</h2>
          <p className="auth-visual-tagline">AI-powered healthcare triage for every corner of India — in Hindi, English, or Hinglish.</p>
          <ul className="auth-visual-features">
            <li><Languages size={18} /> Understands Hindi, English & Hinglish</li>
            <li><Gauge size={18} /> Instant urgency triage in every chat</li>
            <li><MapPin size={18} /> Finds nearby care in seconds</li>
          </ul>
        </div>
      </div>
      <div className="auth-form-panel">
        <div className="auth-card">
          <div className="auth-brand">
            <Logo size={34} />
            <h2>{t('brand_name')}<span>{t('brand_tagline')}</span></h2>
          </div>
          <h1>{t('welcome_back_title')}</h1>
          <p className="auth-subtitle">{t('signin_subtitle')}</p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label><Mail size={13} /> {t('email')}</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            </div>
            <div className="form-group">
              <label><Lock size={13} /> {t('password')}</label>
              <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </div>
            <button type="submit" className="primary-btn auth-submit" disabled={loading}>
              {loading ? t('signing_in') : <>{t('sign_in')} <LogIn size={16} /></>}
            </button>
          </form>

          <p className="auth-switch">{t('no_account')} <Link to="/signup">{t('create_one')}</Link></p>
        </div>
      </div>
    </div>
  );
}

export default Login;
