import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, FileText, ChevronRight, Plus } from 'lucide-react';
import client from '../api/client';
import { useLanguage } from '../context/LanguageContext';

function Reports() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const res = await client.get('/api/reports');
        setReports(res.data);
      } catch (err) {
        setError('Could not load your reports.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="page-container">
      <header className="top-header">
        <div className="header-title">
          <h3>{t('your_reports')}</h3>
          <span>{t('all_saved_consultations')}</span>
        </div>
        <div className="header-profile"><User size={20} /></div>
      </header>

      <div className="content-area">
        <div className="reports-page-toolbar">
          <button className="primary-btn" onClick={() => navigate('/consultation')}>
            <Plus size={16} /> {t('new_consultation_title')}
          </button>
        </div>

        {loading && (
          <div className="empty-state">
            <div className="spinner" />
          </div>
        )}

        {!loading && error && (
          <div className="empty-state">
            <p>{error}</p>
          </div>
        )}

        {!loading && !error && reports.length === 0 && (
          <div className="empty-state">
            <FileText size={40} color="#c7d2e0" />
            <h4>{t('no_reports_title')}</h4>
            <p>{t('no_reports_text')}</p>
            <button className="primary-btn mt-15" onClick={() => navigate('/consultation')}>{t('start_consultation')}</button>
          </div>
        )}

        {!loading && !error && reports.length > 0 && (
          <div className="reports-list-grid">
            {reports.map((r) => (
              <div key={r.id} className="report-list-card" onClick={() => navigate(`/reports/${r.id}`)}>
                <div className="report-list-card-top">
                  <FileText size={22} color="#0066ff" />
                  <div className="urgency-badge small" data-urgency={r.urgency}>{r.urgency}</div>
                </div>
                <h5>{r.predicted_disease}</h5>
                <p className="report-list-meta">{r.patient_name || 'Patient'} • {r.specialist}</p>
                <div className="report-list-card-bottom">
                  <span>{new Date(r.created_at).toLocaleDateString()}</span>
                  <ChevronRight size={16} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Reports;
