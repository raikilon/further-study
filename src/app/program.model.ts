export type Credential = 'CAS' | 'MAS';
export type LanguageCode = 'de' | 'fr' | 'it' | 'en';
export type ProgramFormat = 'in-person' | 'hybrid' | 'online' | 'varies' | null;

export interface Program {
  id: string;
  title: string;
  credential: Credential;
  provider: string;
  providerDomain?: string;
  city: string;
  languages: LanguageCode[];
  subject: string;
  format: ProgramFormat;
  duration: string | null;
  ects: number | null;
  priceCHF: number | null;
  priceNote?: string;
  nextStart: string | null;
  nextStartLabel?: string | null;
  summary: string;
  tags: string[];
  sourceUrl: string;
  verifiedAt: string;
  confidence?: 'high' | 'medium' | 'low';
  catalogStatus?: 'active' | 'not-reconfirmed';
}

export interface ProviderScan {
  name: string;
  domain: string;
  status: 'ok' | 'partial' | 'blocked' | 'error';
  pagesFetched: number;
  paginationPagesFetched?: number;
  paginationAdapters?: string[];
  paginationFindings?: PaginationFinding[];
  robotsDenied?: number;
  programsFound: number;
  note?: string;
}

export interface PaginationFinding {
  provider?: string;
  domain?: string;
  kind: string;
  url: string;
  status: string;
  pagesFetched?: number;
}

export interface ScrapeReport {
  generatedAt: string;
  directorySource: string;
  institutionsDiscovered: number;
  institutionsScanned: number;
  pagesFetched: number;
  paginationPagesFetched?: number;
  paginationFindings?: PaginationFinding[];
  programsFound: number;
  partial: number;
  failures: number;
  providers: ProviderScan[];
}

export interface CatalogData {
  programs: Program[];
  report: ScrapeReport | null;
}
