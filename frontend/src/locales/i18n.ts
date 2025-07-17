import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import heTranslations from './he.json';
import enTranslations from './en.json';

const resources = {
  he: {
    translation: heTranslations,
  },
  en: {
    translation: enTranslations,
  },
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'he', // Default language
    fallbackLng: 'en',
    
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    
    // React i18next options
    react: {
      useSuspense: false,
    },
    
    // Debug in development
    debug: process.env.NODE_ENV === 'development',
  });

export default i18n;