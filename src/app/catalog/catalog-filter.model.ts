import { Credential, LanguageCode, ProgramFormat } from '../program.model';

export type CredentialFilter = '' | Credential;
export type LanguageFilter = '' | LanguageCode;
export type FormatFilter = '' | Exclude<ProgramFormat, null> | 'unknown';
export type ProgramSort = 'start' | 'relevance' | 'price-low' | 'name';

export interface CatalogFilters {
  query: string;
  subject: string;
  provider: string;
  credential: CredentialFilter;
  language: LanguageFilter;
  format: FormatFilter;
  location: string;
  maxFee: number;
}

export interface FilterOption {
  value: string;
  label: string;
}

export const DEFAULT_FILTERS: CatalogFilters = {
  query: '',
  subject: '',
  provider: '',
  credential: '',
  language: '',
  format: '',
  location: '',
  maxFee: 40000,
};
