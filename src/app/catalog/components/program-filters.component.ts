import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CatalogFilters, DEFAULT_FILTERS, FilterOption } from '../catalog-filter.model';

@Component({
  selector: 'app-program-filters',
  standalone: true,
  imports: [CommonModule],
  template: `
    <aside class="filters-panel" aria-label="Program filters">
      <div class="filters-heading"><div><span aria-hidden="true">≡</span><h3>Filters</h3></div><button type="button" class="text-button" (click)="clear.emit()">Clear all</button></div>
      <label class="field-label" for="search-input">Search keywords</label>
      <div class="search-field">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"></circle><path d="m16 16 5 5"></path></svg>
        <input id="search-input" name="query" type="search" [value]="filters.query" (input)="updateText('query', $event)" placeholder="Try ‘data’ or ‘leadership’" />
      </div>
      <div class="filter-group">
        <label class="field-label" for="subject-filter">Subject area</label>
        <select id="subject-filter" name="subject" [value]="filters.subject" (change)="updateSelect('subject', $event)"><option value="">All subject areas</option><option *ngFor="let item of subjects" [value]="item.value">{{ item.label }}</option></select>
      </div>
      <div class="filter-group">
        <label class="field-label" for="provider-filter">Institution</label>
        <select id="provider-filter" name="provider" [value]="filters.provider" (change)="updateSelect('provider', $event)"><option value="">All institutions</option><option *ngFor="let item of providers" [value]="item">{{ item }}</option></select>
      </div>
      <div class="filter-group">
        <label class="field-label" for="credential-filter">Program type</label>
        <select id="credential-filter" name="credential" [value]="filters.credential" (change)="updateSelect('credential', $event)"><option value="">CAS + MAS</option><option value="CAS">CAS only</option><option value="MAS">MAS only</option></select>
      </div>
      <div class="filter-group">
        <label class="field-label" for="language-filter">Teaching language</label>
        <select id="language-filter" name="language" [value]="filters.language" (change)="updateSelect('language', $event)"><option value="">All languages</option><option value="de">German</option><option value="fr">French</option><option value="it">Italian</option><option value="en">English</option></select>
      </div>
      <div class="filter-group">
        <label class="field-label" for="format-filter">Study format</label>
        <select id="format-filter" name="format" [value]="filters.format" (change)="updateSelect('format', $event)"><option value="">Any format</option><option value="in-person">In person</option><option value="hybrid">Hybrid</option><option value="online">Online</option><option value="varies">To be confirmed</option><option value="unknown">Not specified</option></select>
      </div>
      <div class="filter-group">
        <label class="field-label" for="location-filter">Location</label>
        <input class="plain-input" id="location-filter" name="location" type="search" [value]="filters.location" (input)="updateText('location', $event)" placeholder="City or canton" />
      </div>
      <div class="filter-group budget-filter">
        <label class="field-label" for="budget-filter">Maximum fee <span>{{ filters.maxFee >= 40000 ? 'Any' : ('CHF ' + (filters.maxFee | number)) }}</span></label>
        <input id="budget-filter" name="budget" type="range" min="0" max="40000" step="500" [value]="filters.maxFee" (input)="updateFee($event)" />
        <div class="range-labels"><span>CHF 0</span><span>CHF 40,000+</span></div>
      </div>
      <p class="filter-footnote">Filters use information published by providers. A missing value won’t exclude a program.</p>
    </aside>
  `,
})
export class ProgramFiltersComponent {
  @Input() filters: CatalogFilters = { ...DEFAULT_FILTERS };
  @Input() subjects: FilterOption[] = [];
  @Input() providers: string[] = [];
  @Output() filtersChange = new EventEmitter<Partial<CatalogFilters>>();
  @Output() clear = new EventEmitter<void>();

  updateText(key: 'query' | 'location', event: Event): void {
    this.filtersChange.emit({ [key]: this.readValue(event) });
  }

  updateSelect(key: 'subject' | 'provider' | 'credential' | 'language' | 'format', event: Event): void {
    this.filtersChange.emit({ [key]: this.readValue(event) } as Partial<CatalogFilters>);
  }

  updateFee(event: Event): void {
    this.filtersChange.emit({ maxFee: Number(this.readValue(event)) });
  }

  private readValue(event: Event): string {
    return (event.target as HTMLInputElement | HTMLSelectElement).value;
  }
}
