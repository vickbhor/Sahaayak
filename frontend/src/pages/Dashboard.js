import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, FileText } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import client from '../api/client';

function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { t } = useLanguage();
  const [reports, setReports] = useState([]);
  const [latestVitals, setLatestVitals] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await client.get('/api/reports');
        setReports(res.data);
        if (res.data.length > 0) {
          try {
            const detail = await client.get(`/api/reports/${res.data[0].id}`);
            setLatestVitals(detail.data.vitals || {});
          } catch (innerErr) {
            setLatestVitals({});
          }
        }
      } catch (err) {
        setReports([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const latest = reports[0];
  const hasVitals = latestVitals && Object.values(latestVitals).some((v) => v);

  return (
    <div className="page-container">
      <header className="top-header">
        <div className="header-title">
          <h3>{t('dashboard_title')}</h3>
        </div>
        <div className="header-profile"><User size={20} /></div>
      </header>

      <div className="content-area dashboard-content">
        <div className="welcome-banner">
          <div>
            <h1>{t('welcome_back')}{user?.name ? `, ${user.name.split(' ')[0]}` : ''}</h1>
            <p>
              {latest
                ? t('overview_with_report', { disease: latest.predicted_disease })
                : t('overview_no_report')}
            </p>
            <button className="primary-btn mt-15" onClick={() => navigate('/consultation')}>{t('start_consultation')}</button>
          </div>
          <div className="banner-image-placeholder">
            <User size={60} color="#0066ff" />
          </div>
        </div>

        <div className="dashboard-grid">
          <div className="insight-card">
            <h4>✨ {t('ai_insight_title')}</h4>
            {latest ? (
              <>
                <p>
                  {t('insight_prefix')} <strong>{latest.predicted_disease}</strong> {t('insight_suffix')} <strong>{latest.specialist}</strong>.
                </p>
                <span className={`badge ${latest.urgency === 'LOW' || latest.urgency === 'MEDIUM' ? 'positive' : 'urgent'}`}>
                  {latest.urgency === 'LOW' || latest.urgency === 'MEDIUM' ? t('stable_trend') : t('needs_attention')}
                </span>
              </>
            ) : (
              <p>{!loading ? t('no_insight_yet') : ''}</p>
            )}
          </div>
          <div className="vitals-card">
            <h4>{t('latest_vitals')}</h4>
            {hasVitals ? (
              Object.entries(latestVitals).map(([key, value]) =>
                value ? (
                  <div className="vital-row" key={key}>
                    <span>{t(key) !== key ? t(key) : key.replace('_', ' ')}</span>
                    <strong>{value}</strong>
                  </div>
                ) : null
              )
            ) : (
              !loading && <p className="empty-vitals-text">{t('no_vitals_yet')}</p>
            )}
          </div>
        </div>

        <div className="recent-reports">
          <h4>{t('recent_reports')}</h4>
          {!loading && reports.length === 0 && (
            <p className="empty-vitals-text">{t('no_reports_dashboard')}</p>
          )}
          <div className="reports-flex">
            {reports.slice(0, 3).map((r) => (
              <div className="mini-report-card" key={r.id} onClick={() => navigate(`/reports/${r.id}`)}>
                <FileText size={24} color="#555" />
                <div>
                  <h5>{r.predicted_disease}</h5>
                  <p>{new Date(r.created_at).toLocaleDateString()} • {r.specialist}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
