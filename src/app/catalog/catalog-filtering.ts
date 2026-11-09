import { Program } from '../program.model';
import { CatalogFilters, ProgramSort } from './catalog-filter.model';
import { SUBJECT_LABELS } from './catalog-labels';

export function filterPrograms(programs: Program[], filters: CatalogFilters): Program[] {
  const query = filters.query.trim().toLocaleLowerCase();
  const location = filters.location.trim().toLocaleLowerCase();

  return programs.filter((program) => {
    const searchable = [
      program.title,
      program.provider,
      program.city,
      program.summary,
      SUBJECT_LABELS[program.subject] ?? program.subject,
      ...program.tags,
    ].join(' ').toLocaleLowerCase();

    if (query && !searchable.includes(query)) return false;
    if (filters.subject && program.subject !== filters.subject) return false;
    if (filters.provider && program.provider !== filters.provider) return false;
    if (filters.credential && program.credential !== filters.credential) return false;
    if (filters.language && !program.languages.includes(filters.language)) return false;
    if (filters.format === 'unknown' && program.format !== null) return false;
    if (filters.format && filters.format !== 'unknown' && program.format !== filters.format) return false;
    if (location && !program.city.toLocaleLowerCase().includes(location)) return false;
    if (filters.maxFee < 40000 && program.priceCHF !== null && program.priceCHF > filters.maxFee) return false;
    return true;
  });
}

export function sortPrograms(programs: Program[], sortBy: ProgramSort, searchQuery: string): Program[] {
  const query = searchQuery.trim().toLocaleLowerCase();
  return [...programs].sort((a, b) => {
    if (sortBy === 'name') return a.title.localeCompare(b.title);
    if (sortBy === 'price-low') return (a.priceCHF ?? Number.MAX_SAFE_INTEGER) - (b.priceCHF ?? Number.MAX_SAFE_INTEGER);
    if (sortBy === 'relevance' && query) return relevance(b, query) - relevance(a, query) || startOrder(a, b);
    return startOrder(a, b);
  });
}

export function countActiveFilters(filters: CatalogFilters): number {
  const textAndSelects = [filters.query, filters.subject, filters.provider, filters.credential, filters.language, filters.format, filters.location];
  return textAndSelects.filter(Boolean).length + (filters.maxFee < 40000 ? 1 : 0);
}

function relevance(program: Program, query: string): number {
  const title = program.title.toLocaleLowerCase();
  if (title.startsWith(query)) return 3;
  if (title.includes(query)) return 2;
  return 1;
}

function startOrder(a: Program, b: Program): number {
  return (a.nextStart ?? '9999-12-31').localeCompare(b.nextStart ?? '9999-12-31') || a.title.localeCompare(b.title);
}
