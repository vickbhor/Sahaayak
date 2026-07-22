import React, { useState } from 'react';
import { User, MapPin, Navigation, Search, Phone, Building2, AlertCircle, Copy } from 'lucide-react';
import client from '../api/client';
import { useLanguage } from '../context/LanguageContext';

function Support() {
  const { t } = useLanguage();
  const [status, setStatus] = useState('idle');
  const [manualQuery, setManualQuery] = useState('');
  const [hospitals, setHospitals] = useState([]);
  const [locationLabel, setLocationLabel] = useState('');
  const [error, setError] = useState('');
  const [copiedIdx, setCopiedIdx] = useState(null);

  const fetchNearby = async (lat, lon) => {
    setStatus('loading');
    setError('');
    try {
      const res = await client.get('/api/hospitals/nearby', { params: { lat, lon } });
      setHospitals(res.data.results || []);
      setStatus('done');
    } catch (err) {
      setError('Could not fetch nearby hospitals right now. Please try again in a moment.');
      setStatus('error');
    }
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      setError('Location is not supported on this browser. Please search by city instead.');
      setStatus('error');
      return;
    }
    setStatus('requesting');
    setError('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocationLabel('Your current location');
        fetchNearby(pos.coords.latitude, pos.coords.longitude);
      },
      () => {
        setError('Location permission denied. Please search by city or area instead.');
        setStatus('error');
      },
      { timeout: 10000 }
    );
  };

  const searchManual = async (e) => {
    e.preventDefault();
    if (!manualQuery.trim()) return;
    setStatus('loading');
    setError('');
    try {
      const res = await client.get('/api/hospitals/search', { params: { query: manualQuery } });
      setLocationLabel(res.data.location?.display_name || manualQuery);
      setHospitals(res.data.results || []);
      setStatus('done');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not find that location. Try a nearby city or landmark.');
      setStatus('error');
    }
  };

  const copyNumber = (phone, idx) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(phone);
    }
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  };

  return (
    <div className="page-container">
      <header className="top-header">
        <div className="header-title">
          <h3>{t('support_title')}</h3>
          <span>{t('support_subtitle')}</span>
        </div>
        <div className="header-profile"><User size={20} /></div>
      </header>

      <div className="content-area">
        <div className="support-locate-card">
          <MapPin size={26} color="#0066ff" />
          <h2>{t('where_are_you')}</h2>
          <p>{t('share_location_text')}</p>

          <button className="primary-btn support-locate-btn" onClick={useMyLocation} disabled={status === 'requesting' || status === 'loading'}>
            <Navigation size={16} /> {status === 'requesting' ? t('getting_location') : t('use_my_location')}
          </button>

          <div className="support-divider">{t('or')}</div>

          <form className="support-search-row" onSubmit={searchManual}>
            <input
              type="text"
              placeholder={t('search_placeholder')}
              value={manualQuery}
              onChange={(e) => setManualQuery(e.target.value)}
            />
            <button type="submit" className="support-search-btn" disabled={status === 'loading'}><Search size={16} /></button>
          </form>

          {error && (
            <div className="auth-error mt-15 support-error">
              <AlertCircle size={14} /> {error}
            </div>
          )}
        </div>

        {status === 'loading' && (
          <div className="empty-state mt-20"><div className="spinner" /></div>
        )}

        {status === 'done' && (
          <div className="mt-20">
            <p className="support-results-label">{t('showing_results_near')} <strong>{locationLabel}</strong></p>

            {hospitals.length === 0 && (
              <div className="empty-state">
                <Building2 size={40} color="#c7d2e0" />
                <h4>{t('no_hospitals_title')}</h4>
                <p>{t('no_hospitals_text')}</p>
              </div>
            )}

            {hospitals.length > 0 && (
              <div className="hospitals-list">
                {hospitals.map((h, idx) => (
                  <div className="hospital-card" key={idx}>
                    <div className="hospital-card-top">
                      <div className="icon-box"><Building2 size={20} color="#0066ff" /></div>
                      <div className="hospital-card-info">
                        <h5>{h.name}</h5>
                        <p>{h.address || 'Address not available'}</p>
                      </div>
                      <div className="hospital-distance">{h.distance_km} km</div>
                    </div>
                    {h.emergency && <span className="hospital-emergency-badge">{t('emergency_services')}</span>}
                    <div className="hospital-card-actions">
                      {h.phone ? (
                        <>
                          <a href={`tel:${h.phone}`} className="hospital-call-btn"><Phone size={14} /> {t('call_now')} {h.phone}</a>
                          <button className="hospital-copy-btn" onClick={() => copyNumber(h.phone, idx)}>
                            <Copy size={14} /> {copiedIdx === idx ? t('copied') : t('copy')}
                          </button>
                        </>
                      ) : (
                        <span className="hospital-no-phone">{t('phone_not_listed')}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Support;
