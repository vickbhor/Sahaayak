import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { MessageSquare, FileText, Pill, LogOut, Home, HeartHandshake, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import Logo from './Logo';

function Sidebar({ mobileOpen, onClose }) {
  const { user, logout } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className={`sidebar ${mobileOpen ? 'sidebar-mobile-open' : ''}`}>
      <button className="sidebar-mobile-close" onClick={onClose} aria-label="Close menu">
        <X size={20} />
      </button>

      <div className="sidebar-brand">
        <Logo size={30} />
        <h2>{t('brand_name')}<span>{t('brand_tagline')}</span></h2>
      </div>

      <NavLink to="/consultation" className="new-consult-btn" style={{ textDecoration: 'none', textAlign: 'center', display: 'block' }} onClick={onClose}>
        {t('new_consultation')}
      </NavLink>

      <nav className="sidebar-nav">
        <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'active' : '')} onClick={onClose}><Home size={18} /> {t('nav_dashboard')}</NavLink>
        <NavLink to="/consultation" className={({ isActive }) => (isActive ? 'active' : '')} onClick={onClose}><MessageSquare size={18} /> {t('nav_consultation')}</NavLink>
        <NavLink to="/reports" className={({ isActive }) => (isActive ? 'active' : '')} onClick={onClose}><FileText size={18} /> {t('nav_reports')}</NavLink>
        <NavLink to="/medications" className={({ isActive }) => (isActive ? 'active' : '')} onClick={onClose}><Pill size={18} /> {t('nav_medications')}</NavLink>
        <NavLink to="/support" className={({ isActive }) => (isActive ? 'active' : '')} onClick={onClose}><HeartHandshake size={18} /> {t('nav_support')}</NavLink>
      </nav>

      <div className="sidebar-lang-toggle">
        <button className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')}>English</button>
        <button className={language === 'hi' ? 'active' : ''} onClick={() => setLanguage('hi')}>हिन्दी</button>
        <button className={language === 'hinglish' ? 'active' : ''} onClick={() => setLanguage('hinglish')}>Hinglish</button>
      </div>

      <div className="sidebar-bottom">
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">{(user?.name || '?').charAt(0).toUpperCase()}</div>
          <div className="sidebar-user-info">
            <strong>{user?.name || 'Patient'}</strong>
            <span>{user?.email || ''}</span>
          </div>
        </div>
        <button className="sidebar-logout-btn" onClick={handleLogout}><LogOut size={18} /> {t('logout')}</button>
      </div>
    </aside>
  );
}

export default Sidebar;
