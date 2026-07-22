import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { User, Activity, Download, Pill, Leaf, MessageSquare, ThermometerSun, ArrowLeft } from 'lucide-react';
import { jsPDF } from 'jspdf';
import client from '../api/client';
import { useLanguage } from '../context/LanguageContext';
import Logo from '../components/Logo';

function ReportDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await client.get(`/api/reports/${id}`);
      setReport(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load this report.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const downloadPDF = () => {
    if (!report) return;
    const doc = new jsPDF();

    doc.setFillColor(19, 100, 255);
    doc.rect(0, 0, 210, 8, 'F');
    doc.setFillColor(232, 163, 61);
    doc.rect(0, 8, 210, 2, 'F');

    doc.setFontSize(20);
    doc.setTextColor(16, 25, 43);
    doc.text('Dr. Sahaayak', 20, 26);
    doc.setFontSize(10);
    doc.setTextColor(120, 120, 120);
    doc.text('AI HEALTHCARE TRIAGE ASSISTANT', 20, 32);

    doc.setFontSize(10);
    doc.setTextColor(90, 90, 90);
    doc.text(`Report #${report.id}`, 190, 26, null, null, 'right');
    doc.text(new Date(report.created_at).toLocaleDateString(), 190, 32, null, null, 'right');

    doc.setDrawColor(220, 220, 220);
    doc.line(20, 40, 190, 40);

    doc.setFontSize(11);
    doc.setTextColor(0, 0, 0);
    doc.text(`Patient Name: ${report.patient_name || 'N/A'}`, 20, 50);
    doc.text(`Age: ${report.patient_age || '-'}`, 120, 50);
    doc.text(`Gender: ${report.patient_gender || '-'}`, 155, 50);

    doc.setFontSize(26);
    doc.setTextColor(19, 100, 255);
    doc.text('Rx', 20, 68);

    doc.setFontSize(11);
    doc.setTextColor(0, 0, 0);
    doc.text(`Predicted Condition: ${report.predicted_disease}`, 40, 63);
    doc.text(`Urgency Level: ${report.urgency}    |    Confidence: ${(report.confidence * 100).toFixed(0)}%`, 40, 70);
    doc.text(`Recommended Specialist: ${report.specialist}`, 40, 77);

    doc.setFontSize(10.5);
    doc.text('Symptoms Reported:', 20, 90);
    const splitSymptoms = doc.splitTextToSize(report.symptoms_extracted || 'N/A', 165);
    doc.text(splitSymptoms, 20, 97);

    let cursorY = 97 + splitSymptoms.length * 5.5 + 8;

    if (report.vitals && Object.values(report.vitals).some((v) => v)) {
      doc.setFontSize(11.5);
      doc.setTextColor(16, 25, 43);
      doc.text('Vitals Recorded', 20, cursorY);
      cursorY += 7;
      doc.setFontSize(10.5);
      doc.setTextColor(0, 0, 0);
      Object.entries(report.vitals).forEach(([key, value]) => {
        if (value) {
          doc.text(`${key.replace('_', ' ')}: ${value}`, 24, cursorY);
          cursorY += 6;
        }
      });
      cursorY += 6;
    }

    if (report.medicines && report.medicines.length > 0) {
      doc.setFontSize(12);
      doc.setTextColor(19, 100, 255);
      doc.text('Rx  Medicines', 20, cursorY);
      cursorY += 7;
      doc.setFontSize(10.5);
      doc.setTextColor(0, 0, 0);
      report.medicines.forEach((med) => {
        const line = doc.splitTextToSize(`• ${med.name} - ${med.purpose}`, 165);
        doc.text(line, 24, cursorY);
        cursorY += line.length * 5.5 + 2;
      });
      cursorY += 5;
    }

    if (report.home_remedies && report.home_remedies.length > 0) {
      doc.setFontSize(12);
      doc.setTextColor(61, 122, 99);
      doc.text('Home Remedies & Care', 20, cursorY);
      cursorY += 7;
      doc.setFontSize(10.5);
      doc.setTextColor(0, 0, 0);
      report.home_remedies.forEach((item) => {
        const line = doc.splitTextToSize(`• ${item.name} - ${item.purpose}`, 165);
        doc.text(line, 24, cursorY);
        cursorY += line.length * 5.5 + 2;
      });
      cursorY += 5;
    }

    doc.setDrawColor(220, 220, 220);
    doc.line(20, cursorY, 190, cursorY);
    cursorY += 7;
    doc.setFontSize(8.5);
    doc.setTextColor(140, 140, 140);
    const disclaimer = doc.splitTextToSize(
      'This is an AI-assisted triage tool and NOT a substitute for professional medical advice. In an emergency, contact local emergency services immediately.',
      165
    );
    doc.text(disclaimer, 20, cursorY);

    doc.save('Sahaayak_Diagnostic_Report.pdf');
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="content-area" style={{ justifyContent: 'center', alignItems: 'center' }}>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="page-container">
        <div className="content-area" style={{ justifyContent: 'center', alignItems: 'center' }}>
          <h3>{error || 'Report not found.'}</h3>
          <button className="primary-btn mt-15" onClick={() => navigate('/reports')}>Back to Reports</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <header className="top-header">
        <button className="back-link" onClick={() => navigate('/reports')}><ArrowLeft size={18} /></button>
        <div className="header-title">
          <h3>{t('diagnostic_report')}</h3>
          <span>{t('clinical_assessment')} • {new Date(report.created_at).toLocaleDateString()}</span>
        </div>
        <div className="header-profile"><User size={20} /></div>
      </header>

      <div className="content-area">
        <div className="report-container">
          <div className="rx-letterhead">
            <div className="rx-letterhead-bar" />
            <div className="rx-letterhead-top">
              <div className="rx-letterhead-brand">
                <Logo size={38} />
                <div>
                  <h2>{t('brand_name')}</h2>
                  <span>AI HEALTHCARE TRIAGE ASSISTANT</span>
                </div>
              </div>
              <div className="rx-letterhead-meta">
                <span>Report #{report.id}</span>
                <span>{new Date(report.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            <div className="rx-patient-row">
              <div><label>{t('full_name')}</label><strong>{report.patient_name || 'N/A'}</strong></div>
              <div><label>{t('age')}</label><strong>{report.patient_age || '-'}</strong></div>
              <div><label>{t('gender')}</label><strong>{report.patient_gender || '-'}</strong></div>
              <button className="primary-btn small" onClick={downloadPDF}><Download size={14} /> {t('download_pdf')}</button>
            </div>

            <div className="rx-symbol-row">
              <span className="rx-symbol">℞</span>
              <div className="rx-symbol-content">
                <p className="label">{t('predicted_condition')}</p>
                <h2 className="disease-name">{report.predicted_disease}</h2>
                <div className="symptoms-list">
                  <p className="label">{t('primary_symptoms')}</p>
                  <p>{report.symptoms_extracted}</p>
                </div>
                <div className="rx-badges-row">
                  <div className="urgency-badge" data-urgency={report.urgency}>
                    {t('severity')}: {report.urgency}
                  </div>
                  <div className="rx-confidence-chip">{(report.confidence * 100).toFixed(0)}% {t('ai_confidence')}</div>
                </div>
              </div>
            </div>

            {(report.urgency === 'CRITICAL' || report.urgency === 'HIGH') && (
              <div className="emergency-alert mt-20">
                <strong>🚨 {t('emergency_alert')}</strong> {t('emergency_alert_text', { specialist: report.specialist })}
              </div>
            )}
          </div>

          <div className="action-card">
            <h4>{t('suggested_actions')}</h4>
            <div className="action-item">
              <div className="icon-box"><Activity size={20} color="#0066ff" /></div>
              <div>
                <h5>{t('recommended_specialist')}</h5>
                <p>{t('recommended_specialist_text', { specialist: report.specialist })}</p>
              </div>
            </div>
          </div>

          {report.vitals && Object.values(report.vitals).some((v) => v) && (
            <div className="action-card mt-20">
              <h4><ThermometerSun size={18} /> {t('vitals_recorded')}</h4>
              <div className="vitals-summary-grid">
                {Object.entries(report.vitals).map(([key, value]) =>
                  value ? (
                    <div className="vital-row" key={key}>
                      <span>{t(key) !== key ? t(key) : key.replace('_', ' ')}</span>
                      <strong>{value}</strong>
                    </div>
                  ) : null
                )}
              </div>
            </div>
          )}

          {report.medicines && report.medicines.length > 0 && (
            <div className="rx-remedy-card medicine mt-20">
              <h4><Pill size={18} /> {t('suggested_medicines')}</h4>
              {report.medicines.map((med, idx) => (
                <div className="action-item mt-10" key={idx}>
                  <div className="icon-box"><Pill size={20} color="#0066ff" /></div>
                  <div>
                    <h5>{med.name}</h5>
                    <p>{med.purpose}</p>
                    {med.note && <p className="note-text">{med.note}</p>}
                  </div>
                </div>
              ))}
              <p className="disclaimer-text">{t('medicines_disclaimer')}</p>
            </div>
          )}

          {report.home_remedies && report.home_remedies.length > 0 && (
            <div className="rx-remedy-card remedy mt-20">
              <h4><Leaf size={18} /> {t('home_remedies_title')}</h4>
              {report.home_remedies.map((item, idx) => (
                <div className="action-item mt-10" key={idx}>
                  <div className="icon-box leaf"><Leaf size={20} color="#3D7A63" /></div>
                  <div>
                    <h5>{item.name}</h5>
                    <p>{item.purpose}</p>
                    {item.note && <p className="note-text">{item.note}</p>}
                  </div>
                </div>
              ))}
              <p className="disclaimer-text">{t('remedies_disclaimer')}</p>
            </div>
          )}

          {report.transcript && report.transcript.length > 0 && (
            <div className="action-card mt-20">
              <h4><MessageSquare size={18} /> {t('conversation_transcript')}</h4>
              <div className="transcript-box">
                {report.transcript.map((msg, idx) => (
                  <div key={idx} className={`transcript-line ${msg.role}`}>
                    <strong>{msg.role === 'user' ? t('you') : t('brand_name')}:</strong> {msg.content}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ReportDetail;
