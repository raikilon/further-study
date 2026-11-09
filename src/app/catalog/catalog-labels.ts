import { LanguageCode, ProgramFormat } from '../program.model';

export const SUBJECT_LABELS: Record<string, string> = {
  'ai-data': 'AI & data',
  'business-leadership': 'Business & leadership',
  'health-life-sciences': 'Health & life sciences',
  'arts-society': 'Arts & society',
  sustainability: 'Sustainability',
  other: 'Other / not classified',
};

export const LANGUAGE_LABELS: Record<LanguageCode, string> = {
  de: 'German',
  fr: 'French',
  it: 'Italian',
  en: 'English',
};

export const FORMAT_LABELS: Record<Exclude<ProgramFormat, null>, string> = {
  'in-person': 'In person',
  hybrid: 'Hybrid',
  online: 'Online',
  varies: 'To be confirmed',
};
