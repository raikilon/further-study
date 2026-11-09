import { Component } from '@angular/core';
import { CatalogPageComponent } from './catalog/catalog-page.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CatalogPageComponent],
  template: '<app-catalog-page />',
})
export class AppComponent {}
