import React, { createContext, useContext, useState } from 'react';
import translations from '../i18n/translations';

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('sahaayak_lang') || 'en');

  const changeLanguage = (lang) => {
    localStorage.setItem('sahaayak_lang', lang);
    setLanguage(lang);
  };

  const t = (key, vars) => {
    const dict = translations[language] || translations.en;
    let text = dict[key] !== undefined ? dict[key] : (translations.en[key] || key);
    if (vars) {
      Object.entries(vars).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, v);
      });
    }
    return text;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage: changeLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
