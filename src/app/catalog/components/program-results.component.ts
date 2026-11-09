import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Program } from '../../program.model';
import { ProgramSort } from '../catalog-filter.model';
import { ProgramCardComponent } from './program-card.component';

@Component({
  selector: 'app-program-results',
  standalone: true,
  imports: [CommonModule, ProgramCardComponent],
  template: `
    <div class="results-area">
      <div class="results-toolbar">
        <div class="results-count"><strong>{{ loading ? 'Loading programs…' : (total + (total === 1 ? ' program' : ' programs')) }}</strong><span>in the catalog</span></div>
        <label class="sort-control" for="sort-select">Sort by
          <select id="sort-select" name="sortBy" [value]="sortBy" (change)="sortChange.emit($any($event.target).value)"><option value="start">Soonest start</option><option value="relevance">Relevance</option><option value="price-low">Fee: low to high</option><option value="name">Program name</option></select>
        </label>
      </div>

      <div *ngIf="loading" class="loading-state" role="status">Loading the latest catalog…</div>
      <div *ngIf="error" class="loading-state error-state" role="alert"><strong>Catalog unavailable.</strong> {{ error }}</div>
      <div *ngIf="!loading && !error && total" class="program-grid">
        <app-program-card *ngFor="let program of programs; trackBy: trackProgram" [program]="program" />
      </div>
      <div class="show-more" *ngIf="!loading && !error && programs.length < total">
        <p>Showing {{ programs.length }} of {{ total }} programs</p>
        <button class="button-secondary" type="button" (click)="showMore.emit()">Show 30 more</button>
      </div>
      <div *ngIf="!loading && !error && !total" class="empty-state">
        <span aria-hidden="true">⌕</span><h3>No programs match those filters</h3><p>Try a different search or remove a filter.</p><button class="button-secondary" type="button" (click)="clearFilters.emit()">Clear filters</button>
      </div>
      <p class="data-note">Program details can change. Please verify the latest information on the official institution page before applying.</p>
    </div>
  `,
})
export class ProgramResultsComponent {
  @Input() programs: Program[] = [];
  @Input() total = 0;
  @Input() loading = true;
  @Input() error = '';
  @Input() sortBy: ProgramSort = 'start';
  @Output() sortChange = new EventEmitter<ProgramSort>();
  @Output() showMore = new EventEmitter<void>();
  @Output() clearFilters = new EventEmitter<void>();

  trackProgram(_index: number, program: Program): string {
    return program.id;
  }
}
