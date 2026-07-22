import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, User, Phone, UserPlus, Languages, Gauge, MapPin } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import Logo from '../components/Logo';

function Signup() {
  const { register } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirm) {
      setError('Passwords do not match');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    setLoading(true);
    try {
      await register(form.name, form.email, form.phone, form.password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create account. Please try again.');
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
          <h1>{t('create_account')}</h1>
          <p className="auth-subtitle">{t('signup_subtitle')}</p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label><User size={13} /> {t('full_name')}</label>
              <input type="text" required value={form.name} onChange={update('name')} placeholder="e.g., Rahul Sharma" />
            </div>
            <div className="form-group">
              <label><Mail size={13} /> {t('email')}</label>
              <input type="email" required value={form.email} onChange={update('email')} placeholder="you@example.com" />
            </div>
            <div className="form-group">
              <label><Phone size={13} /> {t('phone_optional')}</label>
              <input type="tel" value={form.phone} onChange={update('phone')} placeholder="+91 90000 00000" />
            </div>
            <div className="form-row">
              <div className="form-group half">
                <label><Lock size={13} /> {t('password')}</label>
                <input type="password" required value={form.password} onChange={update('password')} placeholder="At least 6 characters" />
              </div>
              <div className="form-group half">
                <label><Lock size={13} /> {t('confirm_password')}</label>
                <input type="password" required value={form.confirm} onChange={update('confirm')} placeholder="Repeat password" />
              </div>
            </div>
            <button type="submit" className="primary-btn auth-submit" disabled={loading}>
              {loading ? t('creating_account') : <>{t('create_account_btn')} <UserPlus size={16} /></>}
            </button>
          </form>

          <p className="auth-switch">{t('have_account')} <Link to="/login">{t('sign_in_link')}</Link></p>
        </div>
      </div>
    </div>
  );
}

export default Signup;
