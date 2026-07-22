import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Pill, Leaf, ChevronRight } from 'lucide-react';
import client from '../api/client';
import { useLanguage } from '../context/LanguageContext';

function Medications() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [meds, setMeds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const res = await client.get('/api/medications');
        setMeds(res.data);
      } catch (err) {
        setError('Could not load your medications.');
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
          <h3>{t('medications_title')}</h3>
          <span>{t('medications_subtitle')}</span>
        </div>
        <div className="header-profile"><User size={20} /></div>
      </header>

      <div className="content-area">
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

        {!loading && !error && meds.length === 0 && (
          <div className="empty-state">
            <Pill size={40} color="#c7d2e0" />
            <h4>{t('no_meds_title')}</h4>
            <p>{t('no_meds_text')}</p>
            <button className="primary-btn mt-15" onClick={() => navigate('/consultation')}>{t('start_consultation')}</button>
          </div>
        )}

        {!loading && !error && meds.length > 0 && (
          <>
            <div className="disclaimer-banner">
              {t('disclaimer_banner')}
            </div>
            <div className="medications-list">
              {meds.map((m, idx) => (
                <div className="medication-card" key={idx} onClick={() => navigate(`/reports/${m.report_id}`)}>
                  <div className={`icon-box ${m.type === 'home_remedy' ? 'leaf' : ''}`}>
                    {m.type === 'home_remedy' ? <Leaf size={20} color="#3D7A63" /> : <Pill size={20} color="#0066ff" />}
                  </div>
                  <div className="medication-card-body">
                    <span className={`medication-type-tag ${m.type === 'home_remedy' ? 'remedy' : ''}`}>
                      {m.type === 'home_remedy' ? t('home_remedies_title') : t('suggested_medicines')}
                    </span>
                    <h5>{m.name}</h5>
                    <p>{m.purpose}</p>
                    {m.note && <p className="note-text">{m.note}</p>}
                    <div className="medication-card-meta">
                      <span className="urgency-badge small" data-urgency={m.urgency}>{m.urgency}</span>
                      <span>{m.condition}</span>
                      <span>{new Date(m.date).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <ChevronRight size={18} color="#999" />
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Medications;
