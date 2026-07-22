import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, User, Send, ChevronRight, Sparkles } from 'lucide-react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import VitalsIntake from '../components/VitalsIntake';
import LanguageSelect from '../components/LanguageSelect';

const GREETINGS = {
  en: 'Hello, I am Dr. Sahaayak, your AI medical assistant. How can I help you today?',
  hi: 'नमस्ते, मैं डॉ. सहायक हूँ, आपका एआई मेडिकल असिस्टेंट। मैं आपकी कैसे मदद कर सकता हूँ?',
  hinglish: 'Namaste, main Dr. Sahaayak hoon, aapka AI medical assistant. Aapki kaise madad kar sakta hoon?',
};

function Consultation() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { t, setLanguage } = useLanguage();
  const [stage, setStage] = useState('language'); // 'language' -> 'intake' -> 'chat'
  const [chatLanguage, setChatLanguage] = useState(null); // 'en' | 'hi' | 'hinglish'
  const [patient, setPatient] = useState({ name: '', age: '', gender: '' });
  const [vitals, setVitals] = useState({});
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [suggestReport, setSuggestReport] = useState(false);

  const chatEndRef = useRef(null);
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleLanguageSelect = (langCode) => {
    setChatLanguage(langCode);
    setLanguage(langCode); // syncs the whole app's UI text, not just the chat replies
    setStage('intake');
  };

  const handleIntakeComplete = ({ patient: p, vitals: v }) => {
    setPatient(p);
    setVitals(v);
    setMessages([{ role: 'assistant', content: GREETINGS[chatLanguage] || GREETINGS.en }]);
    setStage('chat');
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await client.post('/api/triage', {
        messages: newMessages,
        generate_report: false,
        vitals,
        preferred_language: chatLanguage
      });
      setMessages((prev) => [...prev, { role: 'assistant', content: response.data.reply }]);
      setSuggestReport(!!response.data.suggest_report);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Server error. Please check that the backend is running.' }]);
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    if (generating) return;
    setGenerating(true);
    try {
      const response = await client.post('/api/triage', {
        messages,
        generate_report: true,
        vitals,
        patient_name: patient.name || user?.name,
        patient_age: patient.age,
        patient_gender: patient.gender,
        preferred_language: chatLanguage
      });
      if (response.data.is_report && response.data.report_id) {
        navigate(`/reports/${response.data.report_id}`);
      } else {
        setMessages((prev) => [...prev, { role: 'assistant', content: response.data.reply }]);
      }
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Could not generate the report right now. Please try again.' }]);
    } finally {
      setGenerating(false);
    }
  };

  if (stage === 'language') {
    return (
      <div className="page-container">
        <header className="top-header">
          <div className="header-title">
            <h3>{t('new_consultation_title')}</h3>
            <span>{t('quick_intake')}</span>
          </div>
          <div className="header-profile"><User size={20} /></div>
        </header>
        <div className="content-area">
          <LanguageSelect onSelect={handleLanguageSelect} />
        </div>
      </div>
    );
  }

  if (stage === 'intake') {
    return (
      <div className="page-container">
        <header className="top-header">
          <div className="header-title">
            <h3>{t('new_consultation_title')}</h3>
            <span>{t('quick_intake')}</span>
          </div>
          <div className="header-profile"><User size={20} /></div>
        </header>
        <div className="content-area">
          <VitalsIntake defaultName={user?.name} onComplete={handleIntakeComplete} />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <header className="top-header">
        <div className="header-title">
          <h3>{t('consultation_title')}</h3>
          <span>{t('ai_online')}</span>
        </div>
        <div className="header-profile"><User size={20} /></div>
      </header>

      <div className="content-area chat-area">
        <div className="chat-container">
          <div className="chat-history">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message-wrapper ${msg.role}`}>
                {msg.role === 'assistant' && <div className="avatar bot-avatar"><Activity size={16} /></div>}
                <div className="message-bubble">{msg.content}</div>
                {msg.role === 'user' && <div className="avatar user-avatar"><User size={16} /></div>}
              </div>
            ))}
            {loading && (
              <div className="message-wrapper assistant">
                <div className="avatar bot-avatar"><Activity size={16} /></div>
                <div className="message-bubble loading-dots">Thinking...</div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-controls">
            {suggestReport && !generating && (
              <div className="report-ready-banner">
                <Sparkles size={15} /> {t('report_ready_hint')}
              </div>
            )}
            {suggestReport && (
              <button className="generate-report-btn" onClick={generateReport} disabled={generating}>
                {generating ? t('generating_report') : t('generate_report')} <ChevronRight size={16} />
              </button>
            )}
            <div className="input-box">
              <input
                type="text"
                placeholder={t('type_placeholder')}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                disabled={loading}
              />
              <button onClick={handleSend} disabled={loading} className="send-btn"><Send size={18} /></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Consultation;
