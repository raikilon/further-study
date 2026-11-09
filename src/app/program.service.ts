import { Injectable } from '@angular/core';
import { CatalogData, Program, ScrapeReport } from './program.model';

@Injectable({ providedIn: 'root' })
export class ProgramService {
  async loadCatalog(): Promise<CatalogData> {
    const programsUrl = new URL('data/programs.json', document.baseURI);
    const reportUrl = new URL('data/scrape-report.json', document.baseURI);
    const [programResponse, reportResponse] = await Promise.all([
      fetch(programsUrl, { cache: 'no-cache' }),
      fetch(reportUrl, { cache: 'no-cache' }).catch(() => null),
    ]);

    if (!programResponse.ok) {
      throw new Error(`Catalog request failed (${programResponse.status}).`);
    }

    const programs = (await programResponse.json()) as Program[];
    let report: ScrapeReport | null = null;
    if (reportResponse?.ok) {
      report = (await reportResponse.json()) as ScrapeReport;
    }
    return { programs, report };
  }
}
