'use client';
import { createContext, useContext, useEffect, useState } from 'react';
import type { Language } from '@/lib/api/contracts';
import { messages } from '@/lib/i18n';
const Preferences = createContext<{
  language: Language;
  easy: boolean;
  setLanguage: (value: Language) => void;
  setEasy: (value: boolean) => void;
}>({ language: 'en', easy: false, setLanguage: () => {}, setEasy: () => {} });
export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>('en');
  const [easy, setEasy] = useState(false);
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dataset.reading = easy ? 'easy' : 'standard';
  }, [language, easy]);
  return (
    <Preferences.Provider value={{ language, easy, setLanguage, setEasy }}>
      {children}
    </Preferences.Provider>
  );
}
export function usePreferences() {
  const context = useContext(Preferences);
  return { ...context, t: messages[context.language] };
}
