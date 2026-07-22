import React from 'react';
import { Languages } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

const OPTIONS = [
  { code: 'en', labelKey: 'lang_option_english', descKey: 'lang_option_english_desc' },
  { code: 'hi', labelKey: 'lang_option_hindi', descKey: 'lang_option_hindi_desc' },
  { code: 'hinglish', labelKey: 'lang_option_hinglish', descKey: 'lang_option_hinglish_desc' },
];

function LanguageSelect({ onSelect }) {
  const { t } = useLanguage();

  return (
    <div className="vitals-intake-wrap">
      <div className="vitals-intake-card">
        <div className="vitals-intake-header">
          <Languages size={26} color="#0066ff" />
          <h2>{t('choose_language_title')}</h2>
          <p>{t('choose_language_subtitle')}</p>
        </div>

        <div className="language-select-grid">
          {OPTIONS.map((opt) => (
            <button
              key={opt.code}
              type="button"
              className="language-option-card"
              onClick={() => onSelect(opt.code)}
            >
              <span className="language-option-label">{t(opt.labelKey)}</span>
              <span className="language-option-desc">{t(opt.descKey)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default LanguageSelect;
