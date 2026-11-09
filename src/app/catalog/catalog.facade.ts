import { computed, Injectable, signal } from '@angular/core';
import { CatalogData, Program, ScrapeReport } from '../program.model';
import { ProgramService } from '../program.service';
import { CatalogFilters, DEFAULT_FILTERS, FilterOption, ProgramSort } from './catalog-filter.model';
import { countActiveFilters, filterPrograms, sortPrograms } from './catalog-filtering';
import { SUBJECT_LABELS } from './catalog-labels';

@Injectable({ providedIn: 'root' })
export class CatalogFacade {
  readonly programs = signal<Program[]>([]);
  readonly report = signal<ScrapeReport | null>(null);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly filters = signal<CatalogFilters>({ ...DEFAULT_FILTERS });
  readonly sortBy = signal<ProgramSort>('start');
  readonly pageSize = signal(30);

  readonly subjects = computed<FilterOption[]>(() => {
    const values = new Set(this.programs().map((program) => program.subject).filter(Boolean));
    return [...values].sort().map((value) => ({ value, label: SUBJECT_LABELS[value] ?? value }));
  });

  readonly providers = computed(() =>
    [...new Set(this.programs().map((program) => program.provider).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
  );

  readonly filteredPrograms = computed(() =>
    sortPrograms(filterPrograms(this.programs(), this.filters()), this.sortBy(), this.filters().query),
  );

  readonly displayedPrograms = computed(() => this.filteredPrograms().slice(0, this.pageSize()));
  readonly activeFilterCount = computed(() => countActiveFilters(this.filters()));

  constructor(private readonly programService: ProgramService) {}

  async load(): Promise<void> {
    try {
      const catalog: CatalogData = await this.programService.loadCatalog();
      this.programs.set(catalog.programs);
      this.report.set(catalog.report);
    } catch (error: unknown) {
      this.error.set(error instanceof Error ? error.message : 'The program catalog could not be loaded.');
    } finally {
      this.loading.set(false);
    }
  }

  updateFilters(update: Partial<CatalogFilters>): void {
    this.filters.update((current) => ({ ...current, ...update }));
    this.pageSize.set(30);
  }

  setSort(sortBy: ProgramSort): void {
    this.sortBy.set(sortBy);
  }

  showMore(): void {
    this.pageSize.update((size) => size + 30);
  }

  clearFilters(): void {
    this.filters.set({ ...DEFAULT_FILTERS });
    this.sortBy.set('start');
    this.pageSize.set(30);
  }
}
