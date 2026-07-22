import React, { useState } from 'react';
import { HeartPulse, Thermometer, Activity, Wind, ChevronRight, SkipForward } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

function VitalsIntake({ defaultName, onComplete }) {
  const { t } = useLanguage();
  const [form, setForm] = useState({
    name: defaultName || '',
    age: '',
    gender: '',
    temperature: '',
    blood_pressure: '',
    heart_rate: '',
    spo2: '',
    allergies: '',
    conditions: ''
  });

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleContinue = () => {
    onComplete({
      patient: { name: form.name || defaultName || '', age: form.age, gender: form.gender },
      vitals: {
        temperature: form.temperature,
        blood_pressure: form.blood_pressure,
        heart_rate: form.heart_rate,
        spo2: form.spo2,
        allergies: form.allergies,
        conditions: form.conditions
      }
    });
  };

  const handleSkip = () => {
    onComplete({
      patient: { name: form.name || defaultName || '', age: '', gender: '' },
      vitals: {}
    });
  };

  return (
    <div className="vitals-intake-wrap">
      <div className="vitals-intake-card">
        <div className="vitals-intake-header">
          <HeartPulse size={26} color="#0066ff" />
          <h2>{t('before_we_begin')}</h2>
          <p>{t('intake_subtitle')}</p>
        </div>

        <div className="vitals-form-grid">
          <div className="form-group">
            <label>{t('full_name')}</label>
            <input type="text" placeholder="e.g., Rahul Sharma" value={form.name} onChange={update('name')} />
          </div>
          <div className="form-row">
            <div className="form-group half">
              <label>{t('age')}</label>
              <input type="number" placeholder="Yrs" value={form.age} onChange={update('age')} />
            </div>
            <div className="form-group half">
              <label>{t('gender')}</label>
              <select value={form.gender} onChange={update('gender')}>
                <option value="">{t('select')}</option>
                <option value="Male">{t('male')}</option>
                <option value="Female">{t('female')}</option>
                <option value="Other">{t('other')}</option>
              </select>
            </div>
          </div>

          <div className="vitals-divider"><Activity size={14} /> {t('vitals_if_known')}</div>

          <div className="form-row">
            <div className="form-group half">
              <label><Thermometer size={13} /> {t('temperature')}</label>
              <input type="text" placeholder="e.g., 99°F" value={form.temperature} onChange={update('temperature')} />
            </div>
            <div className="form-group half">
              <label><HeartPulse size={13} /> {t('heart_rate')}</label>
              <input type="text" placeholder="e.g., 82 bpm" value={form.heart_rate} onChange={update('heart_rate')} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group half">
              <label>{t('blood_pressure')}</label>
              <input type="text" placeholder="e.g., 120/80" value={form.blood_pressure} onChange={update('blood_pressure')} />
            </div>
            <div className="form-group half">
              <label><Wind size={13} /> {t('spo2')}</label>
              <input type="text" placeholder="e.g., 97%" value={form.spo2} onChange={update('spo2')} />
            </div>
          </div>
          <div className="form-group">
            <label>{t('allergies')}</label>
            <input type="text" placeholder="e.g., Penicillin, Dust" value={form.allergies} onChange={update('allergies')} />
          </div>
          <div className="form-group">
            <label>{t('conditions')}</label>
            <input type="text" placeholder="e.g., Diabetes, Asthma" value={form.conditions} onChange={update('conditions')} />
          </div>
        </div>

        <div className="vitals-intake-actions">
          <button className="skip-btn" onClick={handleSkip} type="button"><SkipForward size={16} /> {t('skip_for_now')}</button>
          <button className="primary-btn" onClick={handleContinue} type="button">{t('continue_to_consultation')} <ChevronRight size={16} /></button>
        </div>
      </div>
    </div>
  );
}

export default VitalsIntake;
