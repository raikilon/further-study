import { Component, OnInit } from '@angular/core';
import { CatalogFacade } from './catalog.facade';
import { CatalogNoticeComponent } from './components/catalog-notice.component';
import { ProgramFiltersComponent } from './components/program-filters.component';
import { ProgramResultsComponent } from './components/program-results.component';

@Component({
  selector: 'app-catalog-page',
  standalone: true,
  imports: [CatalogNoticeComponent, ProgramFiltersComponent, ProgramResultsComponent],
  templateUrl: './catalog-page.component.html',
})
export class CatalogPageComponent implements OnInit {
  constructor(readonly catalog: CatalogFacade) {}

  ngOnInit(): void {
    void this.catalog.load();
  }
}
